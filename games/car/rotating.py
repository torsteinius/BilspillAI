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
    path_distance: float = 0.


class PoolPolicy:
    def __init__(self, actor, seed, car_count=5, batch_size=0, batch_backend="rust"):
        self.actor=actor
        self.rng=random.Random(seed)
        self.baseline=type(actor)([*actor.architecture[:-1],1],seed=seed).set_backend(actor.backend)
        self.baseline.weights=[self.rng.gauss(0,.1) for _ in self.baseline.weights]
        self.optimizer=Adam(actor.weight_count,rate=.0003)
        self.baseline_optimizer=Adam(self.baseline.weight_count,rate=.0003)
        self.pending=[]
        self.started=self.completed=0
        self.car_counts=[0]*car_count
        self.batch_size=batch_size
        self.batch_backend=batch_backend
        self.batch_engine=None
        self.batch_updates=0

    def credit(self,record):
        # Consume only new reward. A future collision can add a separate delta.
        if not record.credited or record.reward:
            self.pending.append((record.inputs,record.samples,record.means,record.reward,record.credited))
            record.credited=True
            record.reward=0.

    def update(self,force=False):
        if self.batch_size:
            from .batch_learning import gradients
            while len(self.pending)>=self.batch_size or (force and self.pending):
                batch=self.pending[:self.batch_size];del self.pending[:len(batch)]
                ag,bg=gradients(self,batch)
                self.optimizer.apply(self.actor.weights,ag)
                self.baseline_optimizer.apply(self.baseline.weights,bg)
                self.batch_updates+=1
            return
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


def next_owner(policies,cursor,budget,active_counts=None,max_active=None):
    eligible=[i for i,p in enumerate(policies) if p.started<budget and (active_counts is None or max_active is None or active_counts[i]<max_active)]
    if not eligible:return None,cursor
    minimum=min(active_counts[i] for i in eligible) if active_counts is not None else None
    for delta in range(len(policies)):
        owner=(cursor+delta)%len(policies)
        if owner in eligible and (minimum is None or active_counts[owner]==minimum):
            return owner,(owner+1)%len(policies)
    return None,cursor


def collision_weights(count, mode='uniform50'):
    """Oldest first; truncate the 50-slot schedule and renormalize short lives."""
    if not 0 <= count <= 50:
        raise ValueError('Expected up to 50 history records')
    if mode not in ('uniform50', 'latest20_linear', 'latest25_last10', 'latest40_last25', 'uniform_last3'):
        raise ValueError('Unknown collision credit mode')
    if not count:
        return []
    if mode == 'uniform50':
        return [1./count]*count
    if mode == 'uniform_last3':
        schedule = [0.]*47 + [1./3]*3
    elif mode == 'latest40_last25':
        schedule = [0.]*25 + [.6*i/sum(range(24)) for i in range(24)] + [.4]
    elif mode == 'latest25_last10':
        schedule = [0.]*40 + [.75*i/36 for i in range(9)] + [.25]
    else:
        schedule = [.8*i/sum(range(1,50)) for i in range(1,50)] + [.2]
    weights = schedule[-count:]
    total = sum(weights)
    return [w/total for w in weights]


def wall_distance_weights(history,current_distance,horizon=280.):
    weights=[max(0.,1.-max(0.,current_distance-r.path_distance)/horizon) for r in history]
    total=sum(weights)
    if not total:return [0.]*(len(history)-1)+[1.] if history else []
    return [w/total for w in weights]


def split_wall_distance_weights(history,current_distance,horizon=280.,near=28.):
    """Two equal pots, uniform within 0–2 and 2–20 car lengths."""
    ages=[max(0.,current_distance-r.path_distance) for r in history]
    recent=[1. if age<=near else 0. for age in ages]
    older=[1. if near<age<=horizon else 0. for age in ages]
    a,b=sum(recent),sum(older)
    if not a and not b:return [0.]*(len(history)-1)+[1.] if history else []
    recent_share=.5 if a and b else 1. if a else 0.
    return [(recent_share*r/a if a else 0.)+((1-recent_share)*o/b if b else 0.) for r,o in zip(recent,older)]


def credit_history(history,policies,collision=False,credit_mode='uniform50',penalty=50.,current_distance=0.,recent_history=None):
    recent=list(recent_history or []) if credit_mode=='split_distance20_recent3' else []
    extra=[]
    if collision and history:
        selected=list(history) if credit_mode in ('linear_distance20','split_distance20','split_distance20_recent3') else list(history)[-50:]
        if credit_mode in ('split_distance20','split_distance20_recent3'):weights=split_wall_distance_weights(selected,current_distance,40*app.CAR_RADIUS,4*app.CAR_RADIUS)
        elif credit_mode=='linear_distance20':weights=wall_distance_weights(selected,current_distance,40*app.CAR_RADIUS)
        else:weights=collision_weights(len(selected),credit_mode)
        scale=.5 if recent else 1.
        for record,weight in zip(selected,weights):
            record.reward-=penalty*scale*weight
        if recent:
            known={id(r) for r in history}
            for record in recent:
                record.reward-=penalty*.5/len(recent)
                if id(record) not in known:extra.append(record)
    retired=set()
    for record in [*history,*extra]:
        policy=record.origin or policies[record.owner]
        policy.credit(record)
        if policy not in policies:retired.add(policy)
    for policy in retired:policy.update(force=True)
    if collision:
        history.clear()
        if recent_history is not None:recent_history.clear()


def reward_overtake(history, bonus, mode='latest'):
    """Add only the new bonus; normal credit routes it to the original actors."""
    if mode not in ('latest','uniform50'):
        raise ValueError('Unknown overtaking credit mode')
    if not history or not bonus:
        return
    records=list(history)[-50:] if mode=='uniform50' else [history[-1]]
    share=bonus/len(records)
    for record in records:
        record.reward+=share


def reward_progress(history,bonus):
    if history:
        for record in history:record.reward+=bonus/len(history)


def credit_progress_window(session, bonus):
    """Credit only actual actions in this non-overlapping payout window."""
    window=session['progress_records']
    if bonus:
        if app.SPEED_WEIGHTED_PROGRESS:
            values=session['progress_values'];total=sum(max(0.,v) for v in values)
            for record,value in zip(window,values):record.reward+=bonus*max(0.,value)/total if total else 0.
        else:reward_progress(window,bonus)
        for record in window:record.origin.credit(record)
    window.clear()
    session.pop('progress_values',None)


def progress_payout(session,delta,terminal=False):
    session['progress_pending']+=delta;session['progress_ticks']+=1
    if session['progress_ticks']<10 and not terminal:return 0.
    reward=app.PROGRESS_ONLY_REWARD*max(0.,session['progress_pending'])
    session['progress_pending']=0.;session['progress_ticks']=0
    return reward


def train_generation(actors,steps,attempts,cars,histories,seed,on_attempt=None,history_stride=1,credit_mode='uniform50',scenario=None,wall_credit_mode=None,overtake_reward=0.,overtake_credit='latest',background_models=(),pass_only=False,car_collision_penalty=50.,batch_size=0,batch_backend="rust",continue_survivors=False,balanced_sharing=False,distance_reference=None,policies=None,on_frame=None):
    """Complete `attempts` drives per policy; supplied policies retain learning state."""
    if type(history_stride) is not int or history_stride < 1:
        raise ValueError('History stride must be a positive integer')
    if distance_reference is not None and (not math.isfinite(distance_reference) or distance_reference<=0 or scenario is None):
        raise ValueError('Random distance limits require a positive reference and a restartable scenario')
    limit_rng=random.Random(seed+917633)
    reward_overtake([],0.,overtake_credit)
    if credit_mode not in ('linear_distance20','split_distance20','split_distance20_recent3'):collision_weights(0,credit_mode)
    spatial_history=wall_credit_mode in ('linear_distance20','split_distance20','split_distance20_recent3') or credit_mode in ('linear_distance20','split_distance20','split_distance20_recent3')
    if wall_credit_mode is not None and not spatial_history:collision_weights(0,wall_credit_mode)
    recent_credit=credit_mode=='split_distance20_recent3' or wall_credit_mode=='split_distance20_recent3'
    training_count=len(cars)-len(background_models)
    practice=getattr(scenario,'crash_spawns',None)
    if practice:
        from .crash_spawns import PoseTrail
    if not 1<=training_count<=10:raise ValueError('Expected up to ten training cars')
    if policies is None:
        policies=[PoolPolicy(actor,seed+i,training_count,batch_size,batch_backend) for i,actor in enumerate(actors)]
    elif len(policies)!=len(actors) or any(p.actor is not a for p,a in zip(policies,actors)):
        raise ValueError('Policies must match the supplied actors')
    for p in policies:
        if p.pending:raise ValueError('Flush pending rewards before starting a generation')
        p.started=p.completed=0
        p.car_counts=[0]*training_count
        p.batch_updates=0
    sessions=[None]*len(cars)
    max_shared=math.ceil(training_count/len(policies)) if balanced_sharing else None
    peak_active=[0]*len(policies)
    cursor=0;tick=0;assignment_cursor=0
    records=[]
    from .overtaking import OvertakeTracker
    tracker=OvertakeTracker() if overtake_reward else None
    while any(p.completed<attempts for p in policies):
        if scenario is None:app.restart_crashed(cars,0)
        else:scenario.restart_crashed(cars)
        assigned=False
        for i in [(assignment_cursor+j)%training_count for j in range(training_count)]:
            car=cars[i]
            if sessions[i] is not None or car['crashed']:continue
            active_counts=[sum(s is not None and s['owner']==k for s in sessions) for k in range(len(policies))]
            owner,cursor=next_owner(policies,cursor,attempts,active_counts if balanced_sharing else None,max_shared)
            if owner is None:continue
            if practice:scenario.prepare_drive(cars,i)
            p=policies[owner];p.started+=1;p.car_counts[i]+=1
            peak_active[owner]=max(peak_active[owner],active_counts[owner]+1)
            assigned=True
            sessions[i]=dict(owner=owner,snapshot=clone_network(p.actor),steps=0,distance=0.,reward=0.,progress_pending=0.,progress_ticks=0,progress_records=[],overtakes=0,distance_limit=limit_rng.uniform(.5,1.5)*distance_reference if distance_reference is not None else None,start_pose={k:car[k] for k in ('x','y','heading','direction') if k in car})
            if practice:
                sessions[i].update(trail=PoseTrail(20*app.CAR_RADIUS),spawn_source=car.get('spawn_source','random'),practice_point_id=car.get('practice_point_id'))
                sessions[i]['start_pose']['z']=car.get('z',0.)
                sessions[i]['trail'].append(car)
        if assigned:assignment_cursor=(assignment_cursor+1)%training_count
        active=[s is not None and not c['crashed'] for s,c in zip(sessions,cars)]
        if not any(active):
            raise RuntimeError('All cars blocked from spawning before training budget completed')
        if tracker:tracker.update(cars,advance=False)
        before=[c['travel'] for c in cars]
        before_positions=[(c['x'],c['y'],c.get('z',0.)) for c in cars] if spatial_history else None
        controls=[]
        for i,(session,car) in enumerate(zip(sessions,cars)):
            if i>=training_count:
                net=background_models[i-training_count]
                controls.append(0. if car['crashed'] else app.decode_outputs(net.forward(features(car,cars,net))))
                continue
            if not active[i]:controls.append(0.);continue
            owner=session['owner'];p=policies[owner]
            inputs=features(car,cars)
            # Frozen snapshot: no unfinished drive changes policy mid-flight.
            means=tuple(forward_latent(session['snapshot'],inputs))
            samples=tuple(p.rng.gauss(mean,.15) for mean in means)
            action=app.decode_outputs([math.tanh(z) for z in samples]);controls.append(action)
            current_record=Record(owner,inputs,samples,means,action,origin=p,path_distance=car.get('_credit_distance',0.))
            if app.PROGRESS_ONLY_REWARD:session['progress_records'].append(current_record)
            if recent_credit:car.setdefault('_recent_credit',deque(maxlen=3)).append(current_record)
            # Start a new sample at each policy/snapshot boundary; never assign
            # the new driver's rewards to a record belonging to the previous one.
            if session['steps']==0 or not histories[i] or histories[i][-1].span_steps >= history_stride:
                limit=512 if spatial_history else 50
                horizon=40*app.CAR_RADIUS
                while histories[i] and (len(histories[i])>=limit or (spatial_history and car.get('_credit_distance',0.)-histories[i][0].path_distance>horizon)):
                    old=histories[i].popleft();origin=old.origin or policies[old.owner];origin.credit(old)
                    if origin not in policies:origin.update(force=True)
                    elif p.batch_size:origin.update()
                histories[i].append(current_record)
        # Finished-budget cars are parked while remaining drives finish.
        parked=[(i,c['crashed']) for i,c in enumerate(cars) if i<training_count and not active[i]]
        for i,_ in parked:cars[i]['crashed']=True
        events=[]
        if wall_credit_mode is None and car_collision_penalty==50. and not app.DIRECTIONAL_COLLISIONS and not practice:app.step(cars,[],controls=controls)
        else:app.step(cars,[],controls=controls,events=events)
        # Mixed wall/object contacts keep the longer object history.
        wall_only={i for i,kind,_ in events if kind=='wall'} - {i for i,kind,_ in events if kind not in ('wall','car_rear')}
        car_contacts={i for i,kind,_ in events if kind=='car'}
        passed=tracker.update(cars) if tracker else [0]*len(cars)
        for i,crashed in parked:cars[i]['crashed']=crashed
        if on_frame:
            on_frame(dict(cars=cars,owners=[session['owner'] if session else None for session in sessions],
                          completed=[policy.completed for policy in policies],attempts=attempts,
                          step=max((session['steps']+1 for session in sessions if session),default=0),
                          steps_limit=steps,tick=tick))
        for i,(session,car) in enumerate(zip(sessions,cars)):
            if not active[i]:continue
            if practice:session['trail'].append(car)
            delta=car['travel']-before[i]
            distance_reached=session['distance_limit'] is not None and session['distance']+max(0.,delta)>=session['distance_limit']
            if spatial_history:car['_credit_distance']=car.get('_credit_distance',0.)+math.dist(before_positions[i],(car['x'],car['y'],car.get('z',0.)))
            reward=0. if pass_only else driving_reward(delta,car['crashed'])
            if app.PROGRESS_ONLY_REWARD:
                weighted_delta=delta*(app.progress_speed_multiplier(car) if app.SPEED_WEIGHTED_PROGRESS else 1.)
                if app.SPEED_WEIGHTED_PROGRESS:session.setdefault('progress_values',[]).append(weighted_delta)
                reward=progress_payout(session,weighted_delta,car['crashed'] or session['steps']+1>=steps or distance_reached or car.get('finished',False))
            if car.get('finished',False) and not car['crashed']:reward+=50.
            bonus=overtake_reward*passed[i]
            reward_overtake(histories[i],bonus,overtake_credit)
            session['overtakes']+=passed[i]
            if app.PROGRESS_ONLY_REWARD:
                if session['progress_ticks']==0:credit_progress_window(session,reward)
            else:histories[i][-1].reward+=reward
            histories[i][-1].span_steps+=1
            session['reward']+=reward+bonus;session['distance']+=max(0.,delta);session['steps']+=1
            if car['crashed'] or car.get('finished',False) or session['steps']>=steps or distance_reached:
                owner=session['owner'];p=policies[owner]
                practice_result=None;new_point=None
                if practice:
                    if any(index==i and kind=='wall' for index,kind,_ in events):
                        new_point=practice.add_crash(app.TRACK,scenario.direction,session['trail'].before_crash(),car,
                            getattr(scenario,'training_generation',scenario.generation),car_length=2*app.CAR_RADIUS)
                    practice_result=scenario.finish_drive(car)
                penalty=app.collision_cost(events,i,car_collision_penalty) if app.DIRECTIONAL_COLLISIONS else (car_collision_penalty if i in car_contacts else 50.)
                credit_history(histories[i],policies,collision=car['crashed'],credit_mode=(wall_credit_mode or credit_mode) if i in wall_only else credit_mode,penalty=penalty,current_distance=car.get('_credit_distance',0.),recent_history=car.get('_recent_credit'))
                p.update();p.completed+=1
                row=dict(network=owner,car=i,overtakes=session['overtakes'],attempt=p.completed,steps=session['steps'],
                         collision=car['crashed'],collision_kinds=sorted({kind for index,kind,_ in events if index==i}),distance=session['distance'],
                         reward=session['reward']-(penalty if car['crashed'] else 0.),tick=tick,start_pose=session['start_pose'],distance_limit=session['distance_limit'],end_reason='collision' if car['crashed'] else 'finish' if car.get('finished',False) else 'distance_limit' if distance_reached else 'step_limit')
                if practice:row.update(spawn_source=session['spawn_source'],practice_point_id=session['practice_point_id'],practice_test=practice_result,new_crash_point_id=new_point)
                records.append(row)
                if on_attempt:on_attempt(row)
                sessions[i]=None
                if scenario is not None and (car.get('finished',False) or not continue_survivors or distance_reference is not None or practice):
                    histories[i].clear()
                    if recent_credit:car.pop('_recent_credit',None)
                    if not car['crashed']:scenario.restart_car(cars,i)
        tick+=1
    # Include late collision credit attributed to a policy that already finished.
    for p in policies:
        p.update(force=True) if p.batch_size else p.update()
    return dict(attempts=[p.completed for p in policies],assignments=[p.car_counts for p in policies],
                ticks=tick,records=records,max_concurrent_drives=peak_active,balanced_sharing=balanced_sharing,batch_updates=[p.batch_updates for p in policies])
