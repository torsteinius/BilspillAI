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
    span_steps: int = 0


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


def collision_weights(count, mode='uniform50'):
    """Oldest first; truncate the 50-slot schedule and renormalize short lives."""
    if not 0 <= count <= 50:
        raise ValueError('Expected up to 50 history records')
    if mode not in ('uniform50', 'latest20_linear', 'latest25_last10', 'latest40_last25'):
        raise ValueError('Unknown collision credit mode')
    if not count:
        return []
    if mode == 'uniform50':
        return [1./count]*count
    if mode == 'latest40_last25':
        schedule = [0.]*25 + [.6*i/sum(range(24)) for i in range(24)] + [.4]
    elif mode == 'latest25_last10':
        schedule = [0.]*40 + [.75*i/36 for i in range(9)] + [.25]
    else:
        schedule = [.8*i/sum(range(1,50)) for i in range(1,50)] + [.2]
    weights = schedule[-count:]
    total = sum(weights)
    return [w/total for w in weights]


def credit_history(history,policies,collision=False,credit_mode='uniform50'):
    if collision and history:
        for record,weight in zip(history,collision_weights(len(history),credit_mode)):
            record.reward-=50.*weight
    retired=set()
    for record in history:
        policy=record.origin or policies[record.owner]
        policy.credit(record)
        if policy not in policies:retired.add(policy)
    for policy in retired:policy.update()
    if collision:history.clear()


def train_generation(actors,steps,attempts,cars,histories,seed,on_attempt=None,history_stride=1,credit_mode='uniform50',scenario=None,wall_credit_mode=None):
    """Exactly `attempts` completed drives per policy, with no shared round barrier."""
    if type(history_stride) is not int or history_stride < 1:
        raise ValueError('History stride must be a positive integer')
    collision_weights(0,credit_mode)
    if wall_credit_mode is not None:collision_weights(0,wall_credit_mode)
    policies=[PoolPolicy(actor,seed+i) for i,actor in enumerate(actors)]
    sessions=[None]*len(cars)
    cursor=0;tick=0;assignment_cursor=0
    records=[]
    while any(p.completed<attempts for p in policies):
        if scenario is None:app.restart_crashed(cars,0)
        else:scenario.restart_crashed(cars)
        assigned=False
        for i in [(assignment_cursor+j)%len(cars) for j in range(len(cars))]:
            car=cars[i]
            if sessions[i] is not None or car['crashed']:continue
            owner,cursor=next_owner(policies,cursor,attempts)
            if owner is None:continue
            p=policies[owner];p.started+=1;p.car_counts[i]+=1
            assigned=True
            sessions[i]=dict(owner=owner,snapshot=clone_network(p.actor),steps=0,distance=0.,reward=0.,start_pose={k:car[k] for k in ('x','y','heading','direction') if k in car})
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
            # Start a new sample at each policy/snapshot boundary; never assign
            # the new driver's rewards to a record belonging to the previous one.
            if session['steps']==0 or not histories[i] or histories[i][-1].span_steps >= history_stride:
                if len(histories[i])==50:
                    old=histories[i].popleft();origin=old.origin or policies[old.owner];origin.credit(old)
                    if origin not in policies:origin.update()
                histories[i].append(Record(owner,inputs,samples,means,action,origin=p))
        # Finished-budget cars are parked while remaining drives finish.
        parked=[(i,c['crashed']) for i,c in enumerate(cars) if not active[i]]
        for i,_ in parked:cars[i]['crashed']=True
        events=[]
        if wall_credit_mode is None:app.step(cars,[],controls=controls)
        else:app.step(cars,[],controls=controls,events=events)
        # Mixed wall/object contacts keep the longer object history.
        wall_only={i for i,kind,_ in events if kind=='wall'} - {i for i,kind,_ in events if kind!='wall'}
        for i,crashed in parked:cars[i]['crashed']=crashed
        for i,(session,car) in enumerate(zip(sessions,cars)):
            if not active[i]:continue
            delta=car['travel']-before[i]
            reward=driving_reward(delta,car['crashed'])
            histories[i][-1].reward+=reward
            histories[i][-1].span_steps+=1
            session['reward']+=reward;session['distance']+=max(0.,delta);session['steps']+=1
            if car['crashed'] or session['steps']>=steps:
                owner=session['owner'];p=policies[owner]
                credit_history(histories[i],policies,collision=car['crashed'],credit_mode=wall_credit_mode if i in wall_only else credit_mode)
                p.update();p.completed+=1
                row=dict(network=owner,car=i,attempt=p.completed,steps=session['steps'],
                         collision=car['crashed'],collision_kinds=sorted({kind for index,kind,_ in events if index==i}),distance=session['distance'],
                         reward=session['reward']-(50. if car['crashed'] else 0.),tick=tick,start_pose=session['start_pose'])
                records.append(row)
                if on_attempt:on_attempt(row)
                sessions[i]=None
                if scenario is not None:
                    histories[i].clear()
                    if not car['crashed']:scenario.restart_car(cars,i)
        tick+=1
    # Include late collision credit attributed to a policy that already finished.
    for p in policies:p.update()
    return dict(attempts=[p.completed for p in policies],assignments=[p.car_counts for p in policies],
                ticks=tick,records=records)
