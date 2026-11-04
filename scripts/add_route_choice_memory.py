"""Reconstruct causal memory: migrate landmark choices or initialize action-only from scratch."""
import argparse
import copy
import hashlib
import json
import math
import random
from pathlib import Path

from ai.network import NeuralNetwork
from games.maze.history import VERSION_V3, capacity
from games.maze.training import Trainer, Config
from games.maze.world import Rules
from games.maze.world import Maze


def migrate_model(source, target):
    old = NeuralNetwork.load(source)
    if old.metadata['config'].get('history_choice_memory'):
        raise ValueError('Source already has choice memory')
    if old.metadata['config']['history_sensor_count'] != 4:
        raise ValueError('Expected four sensors')
    slots = (old.architecture[0]-4)//4
    new = NeuralNetwork([4+6*slots, *old.architecture[1:]], seed=old.seed)
    new.metadata = copy.deepcopy(old.metadata)
    new.generation = old.generation
    new.history = copy.deepcopy(old.history)
    old_width, new_width = old.architecture[0], new.architecture[0]
    mapping = list(range(4)) + [4+6*(i//4)+i%4 for i in range(old_width-4)]
    for n in range(old.architecture[1]):
        for i, j in enumerate(mapping):
            new.weights[n*(new_width+1)+j] = old.weights[n*(old_width+1)+i]
        new.weights[n*(new_width+1)+new_width] = old.weights[n*(old_width+1)+old_width]
    new.weights[(new_width+1)*old.architecture[1]:] = old.weights[(old_width+1)*old.architecture[1]:]
    active = [False]*new_width
    for i,j in enumerate(mapping):
        active[j] = old.metadata.get('mutation_active_inputs',[True]*old_width)[i]
    new.metadata.update(observation_version=VERSION_V3, mutation_active_inputs=active,
                        history_hidden_widths=list(old.architecture[1:-1]))
    new.metadata.pop('training_objective',None)
    new.metadata['config']['history_choice_memory'] = True
    new.save(target)
    return new


def fresh_action_model(source, target, seed=20261025, slots=128):
    # Read configuration and layer widths only. No trained parameters are copied.
    old = NeuralNetwork.load(source)
    config = copy.deepcopy(old.metadata['config'])
    config.update(history_choice_memory=False, history_action_memory_steps=slots, seed=seed,
                  width=old.metadata['curriculum']['width'], height=old.metadata['curriculum']['height'])
    config['rules'] = Rules(**config['rules'])
    trainer = Trainer(Config(**config), target)
    model = NeuralNetwork([4+2*slots, *old.architecture[1:]], seed=seed)
    model.metadata = copy.deepcopy(trainer.network.metadata)
    model.metadata['history_hidden_widths'] = list(model.architecture[1:-1])
    if 'normalization' in old.metadata:
        model.metadata['normalization'] = old.metadata['normalization']
    model.metadata['initialization'] = dict(method='independent Gaussian per layer', seed=seed,
        scale='1/sqrt(fan_in)', transferred_weights=False)
    model.metadata['mutation_active_inputs'] = [True]*4+[False]*(2*slots)
    rng=random.Random(seed)
    model.weights=[]
    for a,b in zip(model.architecture,model.architecture[1:]):
        model.weights.extend(rng.gauss(0.,1/math.sqrt(a)) for _ in range((a+1)*b))
    model.save(target)
    return model


def convert(dataset, output, model, *, action_only=False, seed=20261025):
    dataset, output = Path(dataset), Path(output)
    manifest = json.loads((dataset/'manifest.json').read_text())
    if manifest['status'] != 'complete' or manifest.get('student_choice_memory'):
        raise ValueError('Expected complete sensor-only history dataset')
    output.mkdir(parents=True,exist_ok=False)
    migrated = (fresh_action_model(model,output/'student-config.json',seed=seed) if action_only
                else migrate_model(model,output/'student-config.json'))
    row_width = 2 if action_only else 6
    trainer = Trainer.load(output/'student-config.json')
    manifest.update(status='building', student_choice_memory=not action_only, student_memory_row_width=row_width,
                    student_action_memory_steps=128 if action_only else 0,
                    student_input_count=migrated.architecture[0],
                    choice_memory_source=str(dataset.resolve()),
                    choice_memory_update='last 128 relative actions, newest first' if action_only else 'latest observation and chosen relative action per landmark')
    samples=routes=0
    with (output/'successful-routes.jsonl').open('w') as dest, \
         (output/'train.jsonl').open('w') as train, (output/'validation.jsonl').open('w') as validation:
        for line in (dataset/'successful-routes.jsonl').open():
            route=json.loads(line);m=route['maze']
            episode=trainer.make_episode(Maze(m['name'],tuple(m['rows']),tuple(m['start']),m['heading']))
            recorded=[episode.snapshot()]
            for sample in route['samples']:
                assert (episode.x,episode.y,episode.heading)==tuple(sample['pose'][k] for k in ('x','y','heading'))
                sample['observation']=episode.observations()
                sample['history_count']=len(episode.memory)
                episode.apply_outputs([1. if b else -1. for b in sample['target_bits']])
                recorded.append(episode.snapshot());samples+=1
                stream=train if route['split']=='train' else validation
                stream.write(json.dumps(dict(route_id=route['route_id'],attempt=route['attempt'],
                    step=sample['step'],width=m['width'],height=m['height'],
                    observation_native_count=len(sample['observation']),
                    observation=sample['observation']+[0.]*(migrated.architecture[0]-len(sample['observation'])),
                    history_count=sample['history_count'],action=sample['action'],target_bits=sample['target_bits']))+'\n')
            assert episode.escaped
            route['frames']=recorded
            dest.write(json.dumps(route)+'\n');routes+=1
    for w,h in manifest['dimensions']:
        manifest['by_size'][f'{w}x{h}']['native_input_count']=migrated.architecture[0] if action_only else 4+6*capacity(w,h)
    manifest.update(status='complete',student_source=str((output/'student-config.json').resolve()),
                    student_sha256=hashlib.sha256((output/'student-config.json').read_bytes()).hexdigest(),
                    source_model_input_count=migrated.architecture[0])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (output/'audit.json').write_text(json.dumps(dict(routes=routes,samples=samples,all_routes_replayed_to_exit=True),indent=2))
    return dict(routes=routes,samples=samples,inputs=migrated.architecture[0])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--model',required=True,type=Path)
    p.add_argument('--action-only',action='store_true')
    p.add_argument('--seed',type=int,default=20261025)
    a=p.parse_args();print(convert(a.dataset,a.output,a.model,action_only=a.action_only,seed=a.seed))
