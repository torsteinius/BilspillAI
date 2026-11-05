"""Five independent learners: safe driving rewards, last-50 credit, elite selection."""
import argparse
from collections import deque
import json
import math
from pathlib import Path
import random
import time

from ai.network import NeuralNetwork
from . import app
from .temporal import Adam, Experience, distribute_collision, forward_gradient

SAFE_REWARD = .02
PROGRESS_REWARD = .05
COLLISION_PENALTY = 50.


def driving_reward(delta, collided):
    # Safe time and signed road progress; circling/backwards motion is not progress.
    return (0. if collided else SAFE_REWARD) + PROGRESS_REWARD*delta


def features(car, cars):
    readings = app.observations(car,cars)
    return [1-d/180 for d in readings[:7]] + readings[7:]


def clone_network(source, rng=None, mutation=0.):
    clone = NeuralNetwork(source.architecture,seed=source.seed).set_backend('rust')
    clone.weights = [w+(rng.gauss(0,mutation) if mutation else 0.) for w in source.weights]
    clone.metadata = dict(source.metadata)
    clone.history = []
    clone.metadata.pop('validation',None)
    return clone


class Learner:
    def __init__(self, actor, seed):
        self.actor = actor
        self.rng = random.Random(seed)
        self.baseline = NeuralNetwork([*actor.architecture[:-1],1],seed=seed).set_backend(actor.backend)
        self.baseline.weights = [self.rng.gauss(0,.1) for _ in self.baseline.weights]
        self.optimizer = Adam(actor.weight_count, rate=.0003)
        self.baseline_optimizer = Adam(self.baseline.weight_count, rate=.0003)
        self.attempts = 0
        self.sequence = 0
        self.begin()

    def begin(self, preserve_history=False):
        if not preserve_history:
            self.history = deque()
        self.gradient = [0.]*self.actor.weight_count
        self.baseline_gradient = [0.]*self.baseline.weight_count
        self.count = 0
        self.steps = 0
        self.reward = self.distance = 0.
        self.finished = False

    def finalize(self, entry):
        if entry.committed:
            if entry.reward == 0.:
                return  # Already learned its safe-driving reward; never replay it twice.
            outputs = [forward_gradient(self.actor,entry.inputs,i) for i in range(self.actor.architecture[-1])]
            latents = entry.latent if isinstance(entry.latent,tuple) else (entry.latent,)
            behavior = entry.behavior_mean if isinstance(entry.behavior_mean,tuple) else (entry.behavior_mean,)
            sigma = .15
            log_ratio = sum((z-old)**2-(z-mean)**2 for z,old,(mean,_) in zip(latents,behavior,outputs))/(2*sigma*sigma)
            ratio = math.exp(max(-20.,min(math.log(2.),log_ratio)))
            # Joint steering/braking likelihood, evaluated under current weights.
            for z,(mean,gradient) in zip(latents,outputs):
                for j,g in enumerate(gradient):
                    self.gradient[j] += entry.reward/50.*ratio*(z-mean)/sigma**2*g
            _,bg = forward_gradient(self.baseline,entry.inputs)
            for j,g in enumerate(bg):
                self.baseline_gradient[j] += entry.reward/50.*g
            self.count += 1
            self.reward += entry.reward
            entry.reward = 0.
            return
        advantage = entry.reward/50.-entry.baseline
        for j,g in enumerate(entry.policy_gradient):
            self.gradient[j] += advantage*g
        for j,g in enumerate(entry.baseline_gradient):
            self.baseline_gradient[j] += advantage*g
        self.count += 1
        self.reward += entry.reward
        entry.reward = 0.
        entry.committed = True

    def choose(self, tick, inputs):
        outputs = [forward_gradient(self.actor,inputs,i) for i in range(self.actor.architecture[-1])]
        sigma = .15
        means = tuple(mean for mean,_ in outputs)
        samples = tuple(self.rng.gauss(mean,sigma) for mean in means)
        action = app.decode_outputs([math.tanh(z) for z in samples])
        baseline,bg = forward_gradient(self.baseline,inputs)
        log_gradient = [sum((z-mean)/sigma**2*gradient[j] for z,(mean,gradient) in zip(samples,outputs))
                        for j in range(self.actor.weight_count)]
        if len(self.history)==50:
            self.finalize(self.history.popleft())
        self.history.append(Experience(self.sequence,inputs,action,None,log_gradient,baseline,bg,
                            latent=samples,behavior_mean=means))
        self.sequence += 1
        self.steps += 1
        return action

    def observe(self, delta, collided):
        self.history[-1].reward += driving_reward(delta,collided)
        self.distance += max(0.,delta)
        if collided:
            distribute_collision(self.history,penalty=COLLISION_PENALTY,mode='uniform50')

    def finish(self, collided):
        if self.finished:
            raise RuntimeError('Attempt was already finalized')
        for entry in self.history:
            self.finalize(entry)
        if collided:
            self.history.clear()
        n=max(1,self.count)
        self.optimizer.apply(self.actor.weights,[g/n for g in self.gradient])
        self.baseline_optimizer.apply(self.baseline.weights,[g/n for g in self.baseline_gradient])
        self.attempts += 1
        self.finished = True
        return dict(attempt=self.attempts,steps=self.steps,collision=collided,
                    reward=self.reward,distance=self.distance)


def train_round(learners,steps,offset,cars=None):
    """Keep survivors in place across weight updates; respawn only crashed cars."""
    if cars is None:
        cars=app.initial(offset)
    else:
        app.restart_crashed(cars,offset)
    for learner in learners:
        learner.begin(preserve_history=True)
    results=[None]*len(learners)
    for tick in range(steps):
        active=[not c['crashed'] for c in cars]
        if not any(active):
            break
        previous=[c['travel'] for c in cars]
        controls=[learner.choose(tick,features(c,cars)) if active[i] else 0.
                  for i,(learner,c) in enumerate(zip(learners,cars))]
        app.step(cars,[],controls=controls)
        for i,(learner,c) in enumerate(zip(learners,cars)):
            if not active[i]:
                continue
            learner.observe(c['travel']-previous[i],c['crashed'])
            if c['crashed']:
                results[i]=learner.finish(True)
    for i,learner in enumerate(learners):
        if results[i] is None:
            if learner.steps:
                results[i]=learner.finish(False)
            else:
                results[i]=dict(attempt=learner.attempts,steps=0,collision=False,waiting_for_spawn=True,reward=0.,distance=0.)
    return results


def evaluate_candidate(actor, traffic, steps, offset=0):
    """Every candidate drives every starting slot/speed against frozen opponents."""
    rows=[]
    for role in range(5):
        cars=app.initial(offset)
        reward=distance=0.
        survived=0
        for tick in range(steps):
            # Evaluation still starts from standardized positions, with no respawns.
            controls=[]
            for i,c in enumerate(cars):
                network=actor if i==role else traffic
                controls.append(app.decode_outputs(network.forward(features(c,cars))) if not c['crashed'] else 0.)
            before=cars[role]['travel']
            app.step(cars,[],controls=controls)
            delta=cars[role]['travel']-before
            collided=cars[role]['crashed']
            reward+=driving_reward(delta,collided)
            distance+=max(0.,delta)
            survived=tick+1
            if collided:
                reward-=COLLISION_PENALTY
                break
        rows.append(dict(role=role,reward=reward,distance=distance,steps=survived,
                         collision=cars[role]['crashed']))
    return dict(score=sum(r['reward'] for r in rows),collisions=sum(r['collision'] for r in rows),
                distance=sum(r['distance'] for r in rows),roles=rows)


def evaluate_suite(actor, traffic, steps, offsets):
    """Identical deterministic scenarios for each network; no training here."""
    runs=[dict(offset=offset, **evaluate_candidate(actor,traffic,steps,offset)) for offset in offsets]
    return dict(score=sum(r['score'] for r in runs),
                collisions=sum(r['collisions'] for r in runs),
                distance=sum(r['distance'] for r in runs),
                test_rounds=len(offsets),attempts=len(offsets)*5,runs=runs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--initial-model',type=Path)
    source.add_argument('--fresh-brake',action='store_true',help='Fresh random 23-input, two-output steering/brake network')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--traffic-model',type=Path,help='Keep fixed evaluation opponents when continuing a run')
    parser.add_argument('--hidden',type=int,nargs='+',help='Hidden layer widths for --fresh-brake; default: 8 8')
    parser.add_argument('--rotate',action='store_true',help='Asynchronous round-robin assignment across cars')
    parser.add_argument('--trained-only',action='store_true',help='Choose among trained candidates; keep parent as reference only')
    parser.add_argument('--generations',type=int,default=2)
    parser.add_argument('--rounds',type=int,default=100)
    parser.add_argument('--test-rounds',type=int,default=20)
    parser.add_argument('--steps',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=20261105)
    parser.add_argument('--generation-offset',type=int,default=0)
    args=parser.parse_args()
    if args.hidden is not None and (not args.fresh_brake or any(width<1 for width in args.hidden)):
        parser.error('--hidden requires --fresh-brake and positive layer widths')
    if args.generation_offset < 0:
        parser.error('Generation offset must be nonnegative')
    if min(args.generations,args.rounds,args.test_rounds,args.steps)<1:
        parser.error('Counts must be positive')
    if args.output.exists():
        parser.error('Output must be a new directory')
    if args.fresh_brake:
        parent=NeuralNetwork([23,*(args.hidden or [8,8]),2],seed=args.seed).set_backend('rust')
        initialization=random.Random(args.seed)
        parent.weights=[initialization.gauss(0,.35) for _ in parent.weights]
        parent.metadata.update(game='car',track='training',traffic='convoy',radar_scale=3.,action_version='steering_brake_0_to_50_v1')
    else:
        parent=NeuralNetwork.load(args.initial_model).set_backend('rust')
    if parent.architecture[0] not in (11,23) or parent.architecture[-1] not in (1,2):
        parser.error('Expected 11 or 23 input cone-radar model with one or two outputs')
    if not args.fresh_brake and parent.metadata.get('observation_version') != 'seven_rays_four_relative_targets_v6':
        parser.error('Relative-speed inputs differ from older checkpoints; use --fresh-brake for this experiment')
    source_generation=parent.generation
    if parent.architecture[0]==11:
        original=parent
        parent=original.expand_inputs(12).set_backend('rust')
        parent.metadata=dict(original.metadata)
        parent.generation=original.generation
        parent.score=original.score
    parent.metadata.update(radar_mode='cone4relative',observation_version='seven_rays_four_relative_targets_v6')
    args.output.mkdir(parents=True)
    parent.save(args.output/'initial.json')
    app.configure_track('training',args.steps);app.configure_traffic('convoy')
    app.configure_radar(3.);app.RADAR_MODE='cone4relative';app.TRACK.set_backend('rust')
    rng=random.Random(args.seed)
    test_rng=random.Random(args.seed+1)
    test_offsets=[test_rng.uniform(-12.,12.) for _ in range(args.test_rounds)]
    settings=dict(engine='rust_gradients_radar_collisions_v1',traffic_model=str(args.traffic_model) if args.traffic_model else None,rotating_networks=args.rotate,trained_candidates_only=args.trained_only,architecture=list(parent.architecture),hidden_layers=list(parent.architecture[1:-1]),weight_count=parent.weight_count,radar_speed_reference='ego_longitudinal_and_radial_relative_velocity',fresh_initialization=args.fresh_brake,action_outputs=parent.architecture[-1],brake_max_reduction=.5 if parent.architecture[-1]==2 else 0.,training_continuation='survivors_keep_pose_and_history_v2',delayed_credit='current_policy_gradient_with_importance_ratio_capped_at_2',radar_targets=4,network_inputs=23,radar_angle_degrees=math.degrees(2*app.CONE_HALF_ANGLE),cone_count=len(app.TRACK.cones),generation_offset=args.generation_offset,test_rounds=args.test_rounds,test_offsets=test_offsets,generations=args.generations,rounds=args.rounds,steps=args.steps,seed=args.seed,
                  learners=5,history=50,credit='uniform50',safe_reward=SAFE_REWARD,
                  progress_reward=PROGRESS_REWARD,collision_penalty=COLLISION_PENALTY,
                  exploration_sigma=.15,learning_rate=.0003,mutation_sigma=.03,
                  initial_generation=source_generation,protected_parent=not args.trained_only,
                  selection='20 test scenarios by default, each in all five slots/speeds against fixed initial-model opponents; no learning or exploration',
                  holdout='Offsets -8 and +8, reported only, not used for selection')
    (args.output/'settings.json').write_text(json.dumps(settings,indent=2))
    traffic=clone_network(NeuralNetwork.load(args.traffic_model) if args.traffic_model else parent)
    if traffic.architecture != parent.architecture or traffic.metadata.get("observation_version") != parent.metadata.get("observation_version"):
        parser.error("Traffic model must use the same architecture and observations")
    traffic.save(args.output/"traffic-reference.json")
    started=time.monotonic()
    with (args.output/'metrics.jsonl').open('w') as log:
        initial=evaluate_suite(parent,traffic,args.steps,test_offsets)
        initial_holdout=[evaluate_candidate(parent,traffic,args.steps,o) for o in (-8,8)]
        log.write(json.dumps(dict(generation=0,evaluation=initial,holdout=initial_holdout))+'\n');log.flush()
        training_cars=app.initial(0)
        learners=[]
        car_histories=[deque() for _ in training_cars]
        for gen in range(args.generation_offset+1,args.generation_offset+args.generations+1):
            previous_learners=learners
            learners=[Learner(clone_network(parent,rng,0. if i==0 else .03),rng.randrange(2**32)) for i in range(5)]
            for current,previous in zip(learners,previous_learners):
                current.history=deque(previous.history)
                current.sequence=previous.sequence
            if args.rotate:
                from .rotating import train_generation
                def report_attempt(row):
                    log.write(json.dumps(dict(generation=gen,training_attempt=row))+'\n');log.flush()
                rotation=train_generation([l.actor for l in learners],args.steps,args.rounds,
                                          training_cars,car_histories,args.seed+gen*100,on_attempt=report_attempt)
                log.write(json.dumps(dict(generation=gen,rotation_summary={k:v for k,v in rotation.items() if k!='records'}))+'\n');log.flush()
            else:
                for round_index in range(args.rounds):
                    stats=train_round(learners,args.steps,0,cars=training_cars)
                    log.write(json.dumps(dict(generation=gen,round=round_index+1,learners=stats))+'\n');log.flush()
            # Evaluate incumbent as reference; eligibility is controlled by --trained-only.
            candidates=[parent]+[l.actor for l in learners]
            evaluations=[]
            for candidate_index,n in enumerate(candidates):
                result=evaluate_suite(n,traffic,args.steps,test_offsets)
                evaluations.append(result)
                log.write(json.dumps(dict(generation=gen,test_candidate=candidate_index,evaluation=result))+'\n');log.flush()
            winner=max(range(1 if args.trained_only else 0,len(candidates)),key=lambda i:evaluations[i]['score'])
            parent=clone_network(candidates[winner])
            parent.generation=gen;parent.score=evaluations[winner]['score']
            parent.metadata.update(training_method='hybrid_uniform50_v1',experiment=settings)
            parent.save(args.output/f'generation-{gen}.json');parent.save(args.output/'model.json')
            for i,learner in enumerate(learners):
                learner.actor.generation=gen
                learner.actor.score=evaluations[i+1]['score']
                learner.actor.metadata.update(training_method='hybrid_uniform50_v1',experiment=settings)
                learner.actor.save(args.output/f'generation-{gen}-learner-{i}.json')
            row=dict(generation=gen,winner='parent' if winner==0 else f'learner-{winner-1}',
                     evaluations=evaluations,holdout=[evaluate_candidate(parent,traffic,args.steps,o) for o in (-8,8)],
                     elapsed_seconds=time.monotonic()-started)
            log.write(json.dumps(row)+'\n');log.flush();print(json.dumps(row),flush=True)
    (args.output/'complete.json').write_text(json.dumps(dict(generations=args.generations,last_generation=args.generation_offset+args.generations,elapsed_seconds=time.monotonic()-started)))


if __name__=='__main__':
    main()
