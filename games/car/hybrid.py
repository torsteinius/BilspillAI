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
        self.baseline = NeuralNetwork(actor.architecture,seed=seed)
        self.baseline.weights = [self.rng.gauss(0,.1) for _ in self.baseline.weights]
        self.optimizer = Adam(actor.weight_count, rate=.0003)
        self.baseline_optimizer = Adam(actor.weight_count, rate=.0003)
        self.attempts = 0
        self.begin()

    def begin(self):
        self.history = deque()
        self.gradient = [0.]*self.actor.weight_count
        self.baseline_gradient = [0.]*self.actor.weight_count
        self.count = 0
        self.reward = self.distance = 0.
        self.finished = False

    def finalize(self, entry):
        advantage = entry.reward/50.-entry.baseline
        for j,g in enumerate(entry.policy_gradient):
            self.gradient[j] += advantage*g
        for j,g in enumerate(entry.baseline_gradient):
            self.baseline_gradient[j] += advantage*g
        self.count += 1
        self.reward += entry.reward

    def choose(self, tick, inputs):
        mean, gradient = forward_gradient(self.actor,inputs)
        sigma = .15
        sample = self.rng.gauss(mean,sigma)
        action = math.tanh(sample)
        baseline,bg = forward_gradient(self.baseline,inputs)
        if len(self.history)==50:
            self.finalize(self.history.popleft())
        self.history.append(Experience(tick,inputs,action,None,
                            [(sample-mean)/sigma**2*g for g in gradient],baseline,bg))
        return action

    def observe(self, delta, collided):
        self.history[-1].reward += driving_reward(delta,collided)
        self.distance += max(0.,delta)
        if collided:
            distribute_collision(self.history,penalty=COLLISION_PENALTY,mode='uniform50')

    def finish(self, collided):
        if self.finished:
            raise RuntimeError('Attempt was already finalized')
        while self.history:
            self.finalize(self.history.popleft())
        n=max(1,self.count)
        self.optimizer.apply(self.actor.weights,[g/n for g in self.gradient])
        self.baseline_optimizer.apply(self.baseline.weights,[g/n for g in self.baseline_gradient])
        self.attempts += 1
        self.finished = True
        return dict(attempt=self.attempts,steps=self.count,collision=collided,
                    reward=self.reward,distance=self.distance)


def train_round(learners,steps,offset):
    """Each car stops at its first collision; everyone starts a new life next round."""
    cars=app.initial(offset)
    for learner in learners:
        learner.begin()
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
            results[i]=learner.finish(False)
    return results


def evaluate_candidate(actor, traffic, steps, offset=0):
    """Every candidate drives every starting slot/speed against frozen opponents."""
    rows=[]
    for role in range(5):
        cars=app.initial(offset)
        reward=distance=0.
        survived=0
        for tick in range(steps):
            # No respawns within an attempt, matching the training round.
            controls=[]
            for i,c in enumerate(cars):
                network=actor if i==role else traffic
                controls.append(network.forward(features(c,cars))[0] if not c['crashed'] else 0.)
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
    parser.add_argument('--initial-model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--generations',type=int,default=2)
    parser.add_argument('--rounds',type=int,default=100)
    parser.add_argument('--test-rounds',type=int,default=20)
    parser.add_argument('--steps',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=20261105)
    args=parser.parse_args()
    if min(args.generations,args.rounds,args.test_rounds,args.steps)<1:
        parser.error('Counts must be positive')
    if args.output.exists():
        parser.error('Output must be a new directory')
    parent=NeuralNetwork.load(args.initial_model).set_backend('rust')
    if parent.architecture!=(11,8,8,1):
        parser.error('Expected 11,8,8,1 cone-radar model')
    args.output.mkdir(parents=True)
    parent.save(args.output/'initial.json')
    app.configure_track('training',args.steps);app.configure_traffic('convoy')
    app.configure_radar(3.);app.RADAR_MODE='cone';app.TRACK.set_backend('rust')
    rng=random.Random(args.seed)
    test_rng=random.Random(args.seed+1)
    test_offsets=[test_rng.uniform(-12.,12.) for _ in range(args.test_rounds)]
    settings=dict(test_rounds=args.test_rounds,test_offsets=test_offsets,generations=args.generations,rounds=args.rounds,steps=args.steps,seed=args.seed,
                  learners=5,history=50,credit='uniform50',safe_reward=SAFE_REWARD,
                  progress_reward=PROGRESS_REWARD,collision_penalty=COLLISION_PENALTY,
                  exploration_sigma=.15,learning_rate=.0003,mutation_sigma=.03,
                  initial_generation=parent.generation,protected_parent=True,
                  selection='20 test scenarios by default, each in all five slots/speeds against fixed initial-model opponents; no learning or exploration',
                  holdout='Offsets -8 and +8, reported only, not used for selection')
    (args.output/'settings.json').write_text(json.dumps(settings,indent=2))
    traffic=clone_network(parent)
    started=time.monotonic()
    with (args.output/'metrics.jsonl').open('w') as log:
        initial=evaluate_suite(parent,traffic,args.steps,test_offsets)
        initial_holdout=[evaluate_candidate(parent,traffic,args.steps,o) for o in (-8,8)]
        log.write(json.dumps(dict(generation=0,evaluation=initial,holdout=initial_holdout))+'\n');log.flush()
        for gen in range(1,args.generations+1):
            learners=[Learner(clone_network(parent,rng,0. if i==0 else .03),rng.randrange(2**32)) for i in range(5)]
            for round_index in range(args.rounds):
                stats=train_round(learners,args.steps,(-8,0,8)[round_index%3])
                log.write(json.dumps(dict(generation=gen,round=round_index+1,learners=stats))+'\n');log.flush()
            # Retest incumbent under the exact same protocol; don't discard a better parent.
            candidates=[parent]+[l.actor for l in learners]
            evaluations=[]
            for candidate_index,n in enumerate(candidates):
                result=evaluate_suite(n,traffic,args.steps,test_offsets)
                evaluations.append(result)
                log.write(json.dumps(dict(generation=gen,test_candidate=candidate_index,evaluation=result))+'\n');log.flush()
            winner=max(range(len(candidates)),key=lambda i:evaluations[i]['score'])
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
    (args.output/'complete.json').write_text(json.dumps(dict(generations=args.generations,elapsed_seconds=time.monotonic()-started)))


if __name__=='__main__':
    main()
