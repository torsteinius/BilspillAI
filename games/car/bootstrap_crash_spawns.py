"""Discover initial practice points by driving the saved model on each road."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
import math
from pathlib import Path
import random

from .crash_spawns import CrashSpawnBank,PoseTrail


def discover(task):
    name,model_path,db_path,seed,minimum,max_attempts=task
    from ai.network import NeuralNetwork
    from . import app
    from .hybrid import features
    from .scenarios import Scenario
    from .temporal import forward_latent
    model=NeuralNetwork.load(model_path).set_backend('rust')
    settings=model.metadata.get('experiment',{})
    app.configure_track(name,1000,cones=False);app.TRACK.set_backend('rust')
    app.configure_traffic('convoy');app.configure_radar(3.);app.RADAR_MODE='laser2';app.ROAD_ONLY=True
    app.MAX_BRAKE=settings.get('brake_max_reduction',.7);app.STEERING_BOOST=settings.get('steering_boost',.5)
    app.LASER_VERTICAL_FAN_DEGREES=model.metadata.get('laser_vertical_fan_degrees',0.)
    bank=CrashSpawnBank(db_path);geometry=bank.register_track(app.TRACK)
    result={}
    for direction in (1,-1):
        def available():
            return bank.db.execute('SELECT count(*) FROM points WHERE track=? AND geometry=? AND direction=? AND tests<?',
                (name,geometry,direction,bank.limit)).fetchone()[0]
        scenario=Scenario(seed,1 if direction==1 else 2,no_cones=True)
        rng=random.Random(seed+direction*8731);cars=scenario.initial()
        trails=[PoseTrail(20*app.CAR_RADIUS) for _ in cars];steps=[0]*len(cars)
        for trail,car in zip(trails,cars):trail.append(car)
        attempts=0
        while available()<minimum and attempts<max_attempts:
            controls=[]
            for car in cars:
                means=forward_latent(model,features(car,cars,model))
                controls.append(app.decode_outputs([math.tanh(rng.gauss(mean,.15)) for mean in means]))
            events=[];app.step(cars,[],controls=controls,events=events)
            wall={index for index,kind,_ in events if kind=='wall'}
            for index,car in enumerate(cars):
                trails[index].append(car);steps[index]+=1
                if car['crashed'] or steps[index]>=1000:
                    attempts+=1
                    if index in wall:
                        bank.add_crash(app.TRACK,direction,trails[index].before_crash(),car,model.generation,
                                       car_length=2*app.CAR_RADIUS)
                    scenario.restart_car(cars,index)
                    trails[index]=PoseTrail(20*app.CAR_RADIUS);trails[index].append(cars[index]);steps[index]=0
            # End discovery as soon as real crashes have supplied enough points.
        result[str(direction)]=dict(points=available(),discovery_drives=attempts)
    bank.db.close()
    return dict(track=name,directions=result)


def main():
    from .training_tracks import TRAINING_TRACKS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--db',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--minimum',type=int,default=2)
    parser.add_argument('--max-attempts',type=int,default=120)
    parser.add_argument('--workers',type=int,default=6)
    parser.add_argument('--seed',type=int,default=20261123)
    args=parser.parse_args()
    bank=CrashSpawnBank(args.db);bank.db.close();results=[]
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        tasks=[(name,str(args.model.resolve()),str(args.db.resolve()),args.seed+i*7919,args.minimum,args.max_attempts)
               for i,name in enumerate(TRAINING_TRACKS)]
        futures=[executor.submit(discover,task) for task in tasks]
        for future in as_completed(futures):
            result=future.result();results.append(result);print(json.dumps(result),flush=True)
    args.output.write_text(json.dumps(results,indent=2)+'\n')
    if any(direction['points']<args.minimum for result in results for direction in result['directions'].values()):
        raise SystemExit('Some roads need additional genuine crash discoveries')


if __name__=='__main__':main()
