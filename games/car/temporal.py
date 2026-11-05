"""Experimental policy-gradient learning with explicitly delayed collision credit.

This is a credit-assignment heuristic, not an unbiased policy gradient of the
original episodic score. Weights stay fixed during an episode. A learned
state baseline predicts the redistributed reward, not a Bellman value.
"""
import argparse
from collections import deque
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import time

from ai.network import NeuralNetwork
from . import app

CREDIT = ((0, .10), (3, .30), (6, .30), (12, .15), (24, .15))
HISTORY = 100


def forward_gradient(network, inputs):
    """Tanh hidden layers, linear final output; gradient of that output."""
    activations = [inputs]
    offsets = []
    offset = 0
    for layer, width in enumerate(network.architecture[1:]):
        offsets.append(offset)
        values = activations[-1]
        stride = len(values)+1
        output = [sum(network.weights[offset+n*stride+i]*v for i,v in enumerate(values))
                  + network.weights[offset+n*stride+stride-1] for n in range(width)]
        activations.append(output if layer == len(network.architecture)-2 else [math.tanh(v) for v in output])
        offset += width*stride
    gradient = [0.]*network.weight_count
    delta = [1.]
    for layer in reversed(range(len(offsets))):
        values = activations[layer]
        stride = len(values)+1
        offset = offsets[layer]
        for n, d in enumerate(delta):
            for i,v in enumerate(values):
                gradient[offset+n*stride+i] = d*v
            gradient[offset+n*stride+stride-1] = d
        if layer:
            delta = [(1-v*v)*sum(network.weights[offset+n*stride+i]*d for n,d in enumerate(delta))
                     for i,v in enumerate(values)]
    return activations[-1][0], gradient


@dataclass
class Experience:
    tick: int
    inputs: list
    action: float
    target_id: str | None
    policy_gradient: list
    baseline: float
    baseline_gradient: list
    reward: float = 0.


def distribute_collision(history, target_id=None, penalty=50., mode='delayed'):
    """Conserve penalty, smooth each lag over ±1 tick; never cross a life reset.

    For an object, restrict to its latest observed encounter, allowing at most
    three missing observations. Unknown/unobserved objects get immediate credit.
    """
    if not history:
        return []
    entries = list(history)
    now = entries[-1].tick
    eligible = entries
    if target_id is not None:
        seen = [e.tick for e in entries if e.target_id == target_id]
        if seen:
            start = last = seen[-1]
            for tick in reversed(seen[:-1]):
                if last-tick > 4:
                    break
                start = last = tick
            eligible = [e for e in entries if start <= e.tick <= seen[-1]]
        else:
            eligible = [entries[-1]]
    allocation = {}
    if mode == 'uniform50':
        recent = entries[-50:]
        allocation = {e.tick: 1./len(recent) for e in recent}
    elif mode == 'immediate':
        allocation[now] = 1.
    else:
        for lag, share in CREDIT:
            desired = now-lag
            nearby = [e for e in eligible if abs(e.tick-desired) <= (0 if lag == 0 else 1)]
            if not nearby:
                nearby = [min(eligible, key=lambda e: abs(e.tick-desired))]
            weights = [2. if e.tick == desired else 1. for e in nearby]
            total = sum(weights)
            for e,w in zip(nearby,weights):
                allocation[e.tick] = allocation.get(e.tick, 0.) + share*w/total
    result = []
    for e in entries:
        amount = penalty*allocation.get(e.tick, 0.)
        if amount:
            e.reward -= amount
            result.append(dict(tick=e.tick, lag=now-e.tick, penalty=amount))
    return result


class Adam:
    def __init__(self, size, rate=.001):
        self.m = [0.]*size
        self.v = [0.]*size
        self.t = 0
        self.rate = rate

    def apply(self, weights, gradient):
        norm = math.sqrt(sum(g*g for g in gradient))
        scale = min(1., .5/max(norm, 1e-12))
        self.t += 1
        for i,g in enumerate(gradient):
            g *= scale
            self.m[i] = .9*self.m[i]+.1*g
            self.v[i] = .999*self.v[i]+.001*g*g
            weights[i] += self.rate*(self.m[i]/(1-.9**self.t))/(math.sqrt(self.v[i]/(1-.999**self.t))+1e-8)


def run_episode(actor, critic, rng, steps, mode, train=True, audit=None, offset=0):
    cars = app.initial(offset)
    histories = [deque() for _ in cars]
    actor_gradient = [0.]*actor.weight_count
    critic_gradient = [0.]*critic.weight_count
    count = collisions = unseen = 0
    distance = total_reward = 0.
    sigma = .25

    def finalize(entry):
        nonlocal count, total_reward
        count += 1
        total_reward += entry.reward
        if not train:
            return
        # Fixed scaling, no hindsight-dependent batch normalization.
        advantage = entry.reward/50.-entry.baseline
        for j,g in enumerate(entry.policy_gradient):
            actor_gradient[j] += advantage*g
        for j,g in enumerate(entry.baseline_gradient):
            critic_gradient[j] += advantage*g

    for tick in range(steps):
        app.restart_crashed(cars, offset)
        for i,c in enumerate(cars):
            c['target_id'] = f"car:{i}:life:{c['restarts']}"
        controls = []
        previous = [c['travel'] for c in cars]
        active = [not c['crashed'] for c in cars]
        for i,c in enumerate(cars):
            if c['crashed']:
                controls.append(0.)
                continue
            radar = app.radar(c,cars)
            readings = app.observations(c,cars)
            inputs = [1-d/180 for d in readings[:7]]+readings[7:]
            mean, gradient = forward_gradient(actor,inputs)
            sample = rng.gauss(mean,sigma) if train else mean
            action = math.tanh(sample)
            controls.append(action)
            baseline, baseline_gradient = forward_gradient(critic,inputs) if train else (0., [])
            # Squashed Gaussian: Jacobian is parameter-independent for fixed action.
            logp_gradient = [(sample-mean)/(sigma*sigma)*g for g in gradient]
            if len(histories[i]) == HISTORY:
                finalize(histories[i].popleft())
            histories[i].append(Experience(tick,inputs,action,radar.get('target_id'),logp_gradient,baseline,baseline_gradient))
        events = []
        app.step(cars,actor.weights,controls=controls,events=events)
        for i,c in enumerate(cars):
            if not active[i]:
                continue
            delta = c['travel']-previous[i]
            distance += max(0.,delta)
            histories[i][-1].reward += .05*delta
            own_events = list(dict.fromkeys((kind,target) for index,kind,target in events if index == i))
            if own_events:
                collisions += 1
                for kind,target in own_events:
                    if kind != 'wall' and not any(e.target_id == target for e in histories[i]):
                        unseen += 1
                    allocation = distribute_collision(histories[i],target,50./len(own_events),mode)
                    if audit is not None:
                        audit.write(json.dumps(dict(tick=tick, car=i, kind=kind, target=target, allocation=allocation))+'\n')
            if c['crashed']:
                while histories[i]:
                    finalize(histories[i].popleft())
    for history in histories:
        while history:
            finalize(history.popleft())
    return (dict(collisions=collisions, distance=distance,
                 collisions_per_1000=1000*collisions/max(distance,1.),
                 reward=total_reward, unobserved_object_events=unseen, samples=count),
            [g/max(count,1) for g in actor_gradient], [g/max(count,1) for g in critic_gradient])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--episodes', type=int, default=30)
    parser.add_argument('--steps', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=20261105)
    parser.add_argument('--credit', choices=('delayed','immediate'), default='delayed')
    parser.add_argument('--initial-model', type=Path, required=True)
    args = parser.parse_args()
    if args.episodes < 1 or args.steps < 1:
        parser.error('Episodes and steps must be positive')
    if args.output.exists():
        parser.error('Use a new output directory; existing runs are preserved')
    actor = NeuralNetwork.load(args.initial_model)
    if actor.architecture != (11,8,8,1):
        parser.error('Expected cone-radar model with architecture 11,8,8,1')
    args.output.mkdir(parents=True)
    actor.save(args.output/'initial.json')
    actor.set_backend('rust')
    app.configure_track('training',args.steps)
    app.configure_traffic('convoy')
    app.configure_radar(3.)
    app.RADAR_MODE = 'cone'
    app.TRACK.set_backend('rust')
    for i,cone in enumerate(app.TRACK.cones):
        cone['target_id'] = f'cone:{i}'
    critic = NeuralNetwork([11,8,8,1],seed=args.seed)
    rng = random.Random(args.seed)
    critic.weights = [rng.gauss(0,.1) for _ in critic.weights]
    actor_optimizer, critic_optimizer = Adam(actor.weight_count), Adam(critic.weight_count)
    settings = dict(credit=args.credit, distribution=CREDIT, history=HISTORY, steps=args.steps,
                    episodes=args.episodes, seed=args.seed, learning_rate=.001, exploration_sigma=.25,
                    progress_reward=.05, collision_penalty=50., initial_generation=actor.generation,
                    method='policy_gradient_with_redistributed_reward_and_state_baseline',
                    limitation='Heuristic action credit, not a causal estimate or Bellman critic')
    (args.output/'settings.json').write_text(json.dumps(settings,indent=2))
    started = time.monotonic()
    with (args.output/'metrics.jsonl').open('w') as log, (args.output/'credit-audit.jsonl').open('w') as audit:
        initial = [run_episode(actor,critic,rng,args.steps,args.credit,False,offset=o)[0] for o in (-8,0,8)]
        log.write(json.dumps(dict(episode=0,evaluation=initial))+'\n');log.flush()
        for episode in range(1,args.episodes+1):
            stats,ag,cg = run_episode(actor,critic,rng,args.steps,args.credit,audit=audit if episode==1 else None)
            actor_optimizer.apply(actor.weights,ag)
            critic_optimizer.apply(critic.weights,cg)
            row = dict(episode=episode,training=stats,elapsed_seconds=time.monotonic()-started)
            if episode % 5 == 0 or episode == args.episodes:
                row['evaluation'] = [run_episode(actor,critic,rng,args.steps,args.credit,False,offset=o)[0] for o in (-8,0,8)]
            log.write(json.dumps(row)+'\n');log.flush()
            actor.generation = episode
            actor.score = stats['reward']
            actor.metadata.update(experiment=settings, training_method='temporal_credit_v1')
            actor.save(args.output/'model.json')
            critic.save(args.output/'baseline.json')
            print(json.dumps(row),flush=True)
    (args.output/'complete.json').write_text(json.dumps(dict(episodes=args.episodes,elapsed_seconds=time.monotonic()-started)))


if __name__ == '__main__':
    main()
