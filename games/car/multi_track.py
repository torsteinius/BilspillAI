"""Balanced practice and repeatable evaluation on several independent roads."""
import math
from contextlib import contextmanager
from collections import deque
from copy import deepcopy

from . import app
from .scenarios import Scenario
from .track import Track


def practice_budgets(names,attempts,generation,start_generation):
    if len(set(names))!=len(names) or attempts<len(names):
        raise ValueError('Each distinct track needs at least one attempt')
    shift=(generation-start_generation)%len(names)
    order=list(names[shift:])+list(names[:shift])
    base,extra=divmod(attempts,len(names))
    return [(name,base+(i<extra)) for i,name in enumerate(order)]


def combine_evaluations(evaluations):
    counts={result['attempts'] for result in evaluations.values()}
    if len(counts)!=1:raise ValueError('Track comparisons require equal evaluation budgets')
    result={key:sum(value.get(key,0) for value in evaluations.values())
            for key in ('score','distance','collisions','overtakes','attempts','test_rounds')}
    result['by_track']={name:{key:value for key,value in evaluation.items() if key!='runs'}
                        for name,evaluation in evaluations.items()}
    result['runs']=[dict(run,track=name) for name,evaluation in evaluations.items()
                    for run in evaluation['runs']]
    return result


class TrackPool:
    def __init__(self,names,steps,seed,crash_spawns=None,crash_spawn_share=.1,standard_starts=False):
        self.standard_starts=standard_starts
        self.names=tuple(names)
        self.steps=steps
        self.seed=seed
        self.crash_spawns=crash_spawns;self.crash_spawn_share=crash_spawn_share
        self.tracks={name:Track.generate(name).set_backend('rust') for name in names}
        for track in self.tracks.values():
            track.cones=[]
            if crash_spawns:crash_spawns.register_track(track)

    def step_limit(self,name):
        track=self.tracks[name]
        # Enough time to reach the finish at ordinary speed, without a return lap.
        return max(self.steps,math.ceil(track.perimeter/3*1.3)) if not track.closed else self.steps

    @contextmanager
    def use(self,name):
        attributes=('TRACK','clearance','progress','PERIMETER','PATH','HALF_WIDTH','SIMULATION_STEPS')
        saved={key:getattr(app,key) for key in attributes}
        saved_status={key:app.status[key] for key in ('track','simulation_steps') if key in app.status}
        track=self.tracks[name]
        app.TRACK=track;app.clearance=track.clearance;app.progress=track.progress
        app.PERIMETER=track.perimeter;app.PATH=track.path;app.HALF_WIDTH=track.half_width
        app.SIMULATION_STEPS=self.step_limit(name)
        app.status.update(track=name,simulation_steps=app.SIMULATION_STEPS)
        try:yield track
        finally:
            for key,value in saved.items():setattr(app,key,value)
            for key in ('track','simulation_steps'):
                if key in saved_status:app.status[key]=saved_status[key]
                else:app.status.pop(key,None)

    def starts(self,rounds,generation=0,holdout=False):
        if rounds%(2*len(self.names)):
            raise ValueError('Evaluation rounds must give every track both directions equally')
        count=rounds//(2*len(self.names));result={}
        for index,name in enumerate(self.names):
            with self.use(name):
                result[name]=[]
                for direction in (1,2):
                    scenario=Scenario(self.seed+900001+index*7919,generation*2+direction,no_cones=True,standard_starts=self.standard_starts)
                    result[name].extend(scenario.evaluation_starts(count,holdout=holdout))
        return result

    def training_scenario(self,name,generation,car_count):
        index=self.names.index(name)
        scenario=Scenario(self.seed+index*7919,2*generation+(generation+index)%2,
                        car_count=car_count,no_cones=True,training_count=car_count,
                        crash_spawns=self.crash_spawns,crash_spawn_share=self.crash_spawn_share,standard_starts=self.standard_starts)
        scenario.training_generation=generation
        return scenario

    def evaluate(self,network,traffic,starts,**kwargs):
        from .hybrid import evaluate_suite
        results={}
        for name in self.names:
            with self.use(name):
                results[name]=evaluate_suite(network,traffic,self.step_limit(name),
                    list(range(len(starts[name]))),starts=starts[name],**kwargs)
        return combine_evaluations(results)


def train_pool_generation(pool,learners,args,generation,on_attempt,on_layout,on_frame=None):
    from .rotating import train_generation
    completed=[0]*len(learners);summaries={};last_scenario=None
    first=getattr(args,'first_training_track',None)
    offset=pool.names.index(first) if first else 0
    order=practice_budgets(pool.names,args.rounds,generation,args.generation_offset+1-offset)
    for name,budget in order:
        with pool.use(name):
            scenario=pool.training_scenario(name,generation,args.training_cars)
            cars=scenario.initial()
            on_layout(name,dict(**scenario.payload(),training_starts=deepcopy(cars)))
            def report(row):
                on_attempt(dict(row,track=name,local_attempt=row['attempt'],
                                attempt=completed[row['network']]+row['attempt']))
            layout=scenario.payload()
            def report_frame(frame):
                on_frame(dict(frame,track=name,generation=generation,scenario=layout,
                    completed=[old+new for old,new in zip(completed,frame['completed'])],attempts=args.rounds))
            result=train_generation([learner.actor for learner in learners],app.SIMULATION_STEPS,budget,
                cars,[deque() for _ in cars],args.seed+generation*100+pool.names.index(name)*100003,
                on_attempt=report,history_stride=args.history_stride,credit_mode=args.collision_credit,
                scenario=scenario,wall_credit_mode=args.wall_credit,pass_only=args.pass_only,
                car_collision_penalty=args.car_collision_penalty,batch_size=args.batch_size,
                batch_backend=args.batch_backend,continue_survivors=args.continue_survivors,
                balanced_sharing=args.balanced_sharing,policies=learners,
                on_frame=report_frame if on_frame else None)
            summaries[name]={key:value for key,value in result.items() if key!='records'}
            completed=[before+after for before,after in zip(completed,result['attempts'])]
            last_scenario=scenario
    return dict(attempts=completed,by_track=summaries,training_order=[name for name,_ in order]),last_scenario
