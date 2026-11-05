"""Asynchronous round-robin policy assignment with car-owned action histories.

Each drive uses frozen behavior weights. Updates use current-policy gradients
and a joint likelihood ratio capped at two; this is an off-policy heuristic.
"""
from collections import deque
from dataclasses import dataclass
import math
import random
from . import app
from .temporal import Adam, forward_gradient, forward_latent
from .hybrid import driving_reward, features, clone_network
from ai.network import NeuralNetwork


@dataclass
class Record:
    owner: int
    inputs: list
    samples: tuple
    means: tuple
    action: object
    reward: float = 0.
    credited: bool = False
    origin: object = None


class PoolPolicy:
    def __init__(self, actor, seed):
        self.actor=actor
        self.rng=random.Random(seed)
        self.baseline=NeuralNetwork([*actor.architecture[:-1],1],seed=seed).set_backend(actor.backend)
        self.baseline.weights=[self.rng.gauss(0,.1) for _ in self.baseline.weights]
        self.optimizer=Adam(actor.weight_count,rate=.0003)
        self.baseline_optimizer=Adam(self.baseline.weight_count,rate=.0003)
        self.pending=[]
        self.started=self.completed=0
        self.car_counts=[0]*5

    def credit(self,record):
        # Consume only new reward. A future collision can add a separate delta.
        if not record.credited or record.reward:
            self.pending.append((record.inputs,record.samples,record.means,record.reward,record.credited))
            record.credited=True
            record.reward=0.

    def update(self):
        if not self.pending:return
        ag=[0.]*self.actor.weight_count;bg=[0.]*self.baseline.weight_count
        sigma=.15
        for inputs,samples,behavior,reward,incremental in self.pending:
            outputs=[forward_gradient(self.actor,inputs,i) for i in range(self.actor.architecture[-1])]
            log_ratio=sum((z-old)**2-(z-mean)**2 for z,old,(mean,_) in zip(samples,behavior,outputs))/(2*sigma*sigma)
            ratio=math.exp(max(-20.,min(math.log(2.),log_ratio)))
            baseline,gradient=forward_gradient(self.baseline,inputs)
            advantage=reward/50.-(0. if incremental else baseline)
            for z,(mean,g) in zip(samples,outputs):
                for j,value in enumerate(g):ag[j]+=ratio*advantage*(z-mean)/sigma**2*value
            for j,value in enumerate(gradient):bg[j]+=advantage*value
        n=len(self.pending)
        self.optimizer.apply(self.actor.weights,[g/n for g in ag])
        self.baseline_optimizer.apply(self.baseline.weights,[g/n for g in bg])
        self.pending.clear()


def next_owner(policies,cursor,budget):
    for delta in range(len(policies)):
        owner=(cursor+delta)%len(policies)
        if policies[owner].started<budget:
            return owner,(owner+1)%len(policies)
    return None,cursor


def credit_history(history,policies,collision=False):
    if collision and history:
        share=50./len(history)
        for record in history:record.reward-=share
    retired=set()
    for record in history:
        policy=record.origin or policies[record.owner]
        policy.credit(record)
        if policy not in policies:retired.add(policy)
    for policy in retired:policy.update()
    if collision:history.clear()


def train_generation(actors,steps,attempts,cars,histories,seed,on_attempt=None):
    """Exactly `attempts` completed drives per policy, with no shared round barrier."""
    policies=[PoolPolicy(actor,seed+i) for i,actor in enumerate(actors)]
    sessions=[None]*len(cars)
    cursor=0;tick=0;assignment_cursor=0
    records=[]
    while any(p.completed<attempts for p in policies):
        app.restart_crashed(cars,0)
        assigned=False
        for i in [(assignment_cursor+j)%len(cars) for j in range(len(cars))]:
            car=cars[i]
            if sessions[i] is not None or car['crashed']:continue
            owner,cursor=next_owner(policies,cursor,attempts)
            if owner is None:continue
            p=policies[owner];p.started+=1;p.car_counts[i]+=1
            assigned=True
            sessions[i]=dict(owner=owner,snapshot=clone_network(p.actor),steps=0,distance=0.,reward=0.)
        if assigned:assignment_cursor=(assignment_cursor+1)%len(cars)
        active=[s is not None and not c['crashed'] for s,c in zip(sessions,cars)]
        if not any(active):
            raise RuntimeError('All cars blocked from spawning before training budget completed')
        before=[c['travel'] for c in cars]
        controls=[]
        for i,(session,car) in enumerate(zip(sessions,cars)):
            if not active[i]:controls.append(0.);continue
            owner=session['owner'];p=policies[owner]
            inputs=features(car,cars)
            # Frozen snapshot: no unfinished drive changes policy mid-flight.
            means=tuple(forward_latent(session['snapshot'],inputs))
            samples=tuple(p.rng.gauss(mean,.15) for mean in means)
            action=app.decode_outputs([math.tanh(z) for z in samples]);controls.append(action)
            if len(histories[i])==50:
                old=histories[i].popleft();origin=old.origin or policies[old.owner];origin.credit(old)
                if origin not in policies:origin.update()
            histories[i].append(Record(owner,inputs,samples,means,action,origin=p))
        # Finished-budget cars are parked while remaining drives finish.
        parked=[(i,c['crashed']) for i,c in enumerate(cars) if not active[i]]
        for i,_ in parked:cars[i]['crashed']=True
        app.step(cars,[],controls=controls)
        for i,crashed in parked:cars[i]['crashed']=crashed
        for i,(session,car) in enumerate(zip(sessions,cars)):
            if not active[i]:continue
            delta=car['travel']-before[i]
            reward=driving_reward(delta,car['crashed'])
            histories[i][-1].reward+=reward
            session['reward']+=reward;session['distance']+=max(0.,delta);session['steps']+=1
            if car['crashed'] or session['steps']>=steps:
                owner=session['owner'];p=policies[owner]
                credit_history(histories[i],policies,collision=car['crashed'])
                p.update();p.completed+=1
                row=dict(network=owner,car=i,attempt=p.completed,steps=session['steps'],
                         collision=car['crashed'],distance=session['distance'],
                         reward=session['reward']-(50. if car['crashed'] else 0.),tick=tick)
                records.append(row)
                if on_attempt:on_attempt(row)
                sessions[i]=None
        tick+=1
    # Include late collision credit attributed to a policy that already finished.
    for p in policies:p.update()
    return dict(attempts=[p.completed for p in policies],assignments=[p.car_counts for p in policies],
                ticks=tick,records=records)
