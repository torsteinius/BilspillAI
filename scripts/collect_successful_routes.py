"""Collect successful demonstrations from an existing, sensor-only legacy walker.

No training, weight changes, shortest-path guidance, or action randomization.
The simulator records the student's landmark history independently of the teacher.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

from ai.network import NeuralNetwork
from games.maze.generator import generate
from games.maze.history import capacity
from games.maze.memory import ANGLES, MOVES, VERSION as WALKER_VERSION
from games.maze.training import Trainer

ACTION_BITS = {'backward': [0, 0], 'right': [0, 1], 'left': [1, 0], 'forward': [1, 1]}


class SensorOnlyWalker:
    def __init__(self, network):
        self.network = network
        if network.metadata.get('observation_version') != WALKER_VERSION:
            raise ValueError('Expected the saved legacy walker with eight rays and six outputs')
        slots = network.metadata['config']['rules']['memory_steps']
        if network.architecture[0] != 8 + 2 * slots or network.architecture[-1] != 6:
            raise ValueError('Unexpected legacy walker architecture')

    def choose(self, normalized_rays):
        if len(normalized_rays) != 8:
            raise ValueError('The teacher needs its original eight sensors')
        # Both stored memory and occupancy markers are zero. The teacher cannot
        # see the student's history, coordinates, score, visited cells or goal.
        inputs = list(normalized_rays) + [0.] * (self.network.architecture[0] - 8)
        outputs = self.network.forward(inputs)
        action = MOVES[max(range(4), key=lambda i: outputs[i])]
        return action, inputs, outputs


def collect_attempt(teacher, trainer, maze, attempt, max_steps=512):
    episode = trainer.make_episode(maze)
    if episode.sensor_count != 4 or episode.output_encoding != 'bits2':
        raise ValueError('Student recording requires four sensors and two output bits')
    route_id = hashlib.sha256('\n'.join(maze.rows).encode()).hexdigest()
    # Entire wall layouts stay on one side of the split, independent of success.
    split = 'validation' if int(route_id[:8], 16) % 10 == 0 else 'train'
    samples, frames = [], [episode.snapshot()]
    while not episode.done and episode.steps < max_steps:
        rays = [maze.ray(episode.x, episode.y, episode.heading, angle) / maze.sensor_range
                for angle in ANGLES]
        action, teacher_inputs, teacher_outputs = teacher.choose(rays)
        bits = ACTION_BITS[action]
        samples.append(dict(step=episode.steps, observation=episode.observations(),
            action=action, target_bits=bits, history_count=len(episode.memory),
            pose=dict(x=episode.x, y=episode.y, heading=episode.heading),
            teacher_inputs=teacher_inputs, teacher_outputs=teacher_outputs))
        episode.apply_outputs([1. if bit else -1. for bit in bits])
        assert episode.last_action == action
        frames.append(episode.snapshot())
    summary = dict(attempt=attempt, route_id=route_id, split=split, maze_name=maze.name,
        width=maze.width, height=maze.height, sensor_range=maze.sensor_range,
        escaped=episode.escaped, clean_success=episode.clean_success, steps=episode.steps,
        score=episode.score, event=episode.event if episode.done else 'Collector safety step limit',
        truncated=not episode.done, action_counts=dict(Counter(episode.actions)))
    # Never turn a failure or a positive partial score into a successful example.
    route = None
    if episode.escaped:
        route = dict(summary, maze=maze.payload(), samples=samples, frames=frames)
    return summary, route


def collect(teacher_path, student_path, output, attempts=1000, seed=202610180100000,
            max_steps=512, sizes=None):
    if attempts < 1 or max_steps < 1:
        raise ValueError('Attempts and maximum steps must be positive')
    teacher_path, student_path, output = map(Path, (teacher_path, student_path, output))
    teacher_bytes = teacher_path.read_bytes()
    teacher = SensorOnlyWalker(NeuralNetwork.load(teacher_path))
    trainer = Trainer.load(student_path)
    if not trainer.config.deterministic_history:
        raise ValueError('Student configuration must use deterministic landmark history')
    sizes = list(sizes) if sizes is not None else None
    if sizes is not None and (not sizes or len(set(sizes)) != len(sizes)
                              or any(type(n) is not int or n < 5 for n in sizes)):
        raise ValueError('Sizes must be distinct integers of at least five')
    dimensions = [(n,n) for n in sizes] if sizes else [(trainer.width,trainer.height)]
    input_count = max(4*(1+capacity(w,h)) for w,h in dimensions)
    student_bytes = student_path.read_bytes()
    # A new directory is mandatory; existing datasets are never overwritten.
    output.mkdir(parents=True, exist_ok=False)
    (output/'teacher.json').write_bytes(teacher_bytes)
    (output/'student-config.json').write_bytes(student_bytes)
    started = time.perf_counter()
    manifest = dict(format_version=2, status='running', teacher_source=str(teacher_path.resolve()),
        teacher_sha256=hashlib.sha256(teacher_bytes).hexdigest(),
        teacher_generation=teacher.network.generation, teacher_architecture=list(teacher.network.architecture),
        teacher_mode='eight normalized rays; all memory and occupancy inputs zero; original argmax',
        randomization='maze layout and initial pose only; deterministic teacher, unchanged weights',
        student_source=str(student_path.resolve()), student_sensor_count=4,
        student_input_count=input_count, source_model_input_count=trainer.network.architecture[0],
        student_config_sha256=hashlib.sha256(student_bytes).hexdigest(),
        observation_padding='append zeros to largest maze capacity; current sensors remain first',
        student_output_encoding='bits2',
        student_memory_decay=trainer.config.history_memory_decay,
        student_memory_floor=trainer.config.history_memory_floor,
        student_newest_first=trainer.config.history_newest_first,
        width=dimensions[0][0] if len(dimensions)==1 else None,
        height=dimensions[0][1] if len(dimensions)==1 else None,
        dimensions=[list(d) for d in dimensions], size_schedule='round_robin', seed_start=seed,
        requested_attempts=attempts, max_steps=max_steps,
        rules=trainer.network.metadata['config']['rules'],
        split_rule='sha256(wall layout) modulo 10: 0 = validation, otherwise train',
        target_meaning='observed actions on successful routes; not guaranteed optimal',
        attempted=0, successes=0, successful_samples=0,
        split_attempts=dict(train=0, validation=0),
        split_successes=dict(train=0, validation=0), split_samples=dict(train=0, validation=0))
    manifest['by_size'] = {f'{w}x{h}':dict(attempted=0,successes=0,successful_samples=0,
        native_input_count=4*(1+capacity(w,h)),truncated=0,
        split_successes=dict(train=0,validation=0),split_samples=dict(train=0,validation=0))
        for w,h in dimensions}
    layouts_by_size = {key:set() for key in manifest['by_size']}
    def save_status():
        for key,stats in manifest['by_size'].items():
            stats['success_rate'] = stats['successes']/max(1,stats['attempted'])
            stats['distinct_layouts'] = len(layouts_by_size[key])
        manifest['elapsed_seconds'] = time.perf_counter()-started
        manifest['success_rate'] = manifest['successes']/max(1, manifest['attempted'])
        temporary = output/'manifest.tmp'
        temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        temporary.replace(output/'manifest.json')
    save_status()
    layouts, actions = set(), Counter()
    current_seed = seed
    try:
        with (output/'attempts.jsonl').open('w') as all_attempts, (output/'successful-routes.jsonl').open('w') as routes, \
             (output/'train.jsonl').open('w') as train, (output/'validation.jsonl').open('w') as validation:
            for attempt in range(1, attempts+1):
                # Independent seeds may produce the same small maze. Count every
                # attempt; hash-based splitting keeps repeats out of the other set.
                width,height = dimensions[(attempt-1) % len(dimensions)]
                maze = generate(width, height, seed=current_seed)
                current_seed += 1
                layouts.add(maze.rows)
                size_key = f'{width}x{height}'
                layouts_by_size[size_key].add(maze.rows)
                stats = manifest['by_size'][size_key]
                summary, route = collect_attempt(teacher, trainer, maze, attempt, max_steps)
                all_attempts.write(json.dumps(summary, ensure_ascii=False)+'\n')
                manifest['attempted'] += 1
                stats['attempted'] += 1
                stats['truncated'] += int(summary['truncated'])
                manifest['split_attempts'][summary['split']] += 1
                actions.update(summary['action_counts'])
                if route is not None:
                    routes.write(json.dumps(route, ensure_ascii=False)+'\n')
                    manifest['successes'] += 1
                    stats['successes'] += 1
                    stats['successful_samples'] += len(route['samples'])
                    stats['split_successes'][summary['split']] += 1
                    stats['split_samples'][summary['split']] += len(route['samples'])
                    manifest['successful_samples'] += len(route['samples'])
                    manifest['split_successes'][summary['split']] += 1
                    manifest['split_samples'][summary['split']] += len(route['samples'])
                    stream = validation if summary['split']=='validation' else train
                    for sample in route['samples']:
                        stream.write(json.dumps(dict(route_id=route['route_id'],attempt=attempt,
                            step=sample['step'], width=width, height=height, sensor_range=maze.sensor_range,
                            observation_native_count=len(sample['observation']),
                            observation=sample['observation']+[0.]*(input_count-len(sample['observation'])),
                            action=sample['action'], target_bits=sample['target_bits']))+'\n')
                if attempt % 100 == 0:
                    for stream in (all_attempts,routes,train,validation):stream.flush()
                    save_status()
                    print(json.dumps(dict(attempts=attempt,successes=manifest['successes'],
                        samples=manifest['successful_samples'])), flush=True)
        assert teacher_path.read_bytes() == teacher_bytes, 'Teacher source changed during collection'
        assert student_path.read_bytes() == student_bytes, 'Student source changed during collection'
        manifest.update(status='complete', next_seed=current_seed, action_counts=dict(actions),
                        distinct_layouts=len(layouts), repeated_layout_attempts=attempts-len(layouts), teacher_unchanged=True)
        save_status()
    except Exception as error:
        manifest.update(status='error', error=str(error)); save_status()
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--teacher',type=Path,required=True)
    parser.add_argument('--student-config',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--attempts',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=202610180100000)
    parser.add_argument('--max-steps',type=int,default=512)
    parser.add_argument('--sizes',type=int,nargs='+',help='Square maze sizes, distributed round-robin')
    args = parser.parse_args()
    report = collect(args.teacher,args.student_config,args.output,args.attempts,args.seed,args.max_steps,args.sizes)
    print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()
