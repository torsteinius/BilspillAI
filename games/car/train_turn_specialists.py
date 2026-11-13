"""Reproducible imitation + on-policy correction for the turn specialists.

A centreline teacher supplies training labels only. Saved policies receive only
sensor observations and speed. Holdout geometry never supplies training labels.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from ai.network import NeuralNetwork
from . import app
from .track import Track
from .turn_sensors import inputs, INPUT_COUNTS, MODES


def use_track(track):
    track.set_backend('rust')
    app.TRACK = track
    app.clearance, app.progress = track.clearance, track.progress
    app.PERIMETER = track.perimeter
    app.ROAD_ONLY = True
    app.STEERING_BOOST = 1.
    app.MAX_BRAKE = .5


def teacher(track, car):
    along = track.progress(car['x'], car['y'], car.get('z', 0.))
    target = track.pose(along+car['direction']*22.)
    dx, dy = target['x']-car['x'], target['y']-car['y']
    lateral = -dx*math.sin(car['heading'])+dy*math.cos(car['heading'])
    yaw = 2*lateral/max(dx*dx+dy*dy, 1.)*(1.8*car['speed_factor'])
    lo, hi = -1., 1.
    for _ in range(20):
        mid = (lo+hi)/2
        if .045*(mid+mid**3)<yaw: lo=mid
        else: hi=mid
    return [(lo+hi)/2, .6]  # brake=(output+1)/2=.8 -> 60% base speed


def spawn(track, along, direction, lateral=0., angle=0., factor=1.):
    return dict(track.pose(along, lateral), direction=direction, speed_factor=factor,
                speed=1.8*factor, travel=0., crashed=False, restarts=0.) | {
                    'heading': track.pose(along)['heading']+(math.pi if direction<0 else 0.)+angle}


def sample_data(tracks, mode, count, rng):
    xs, ys = [], []
    for i in range(count):
        track=tracks[i%len(tracks)]
        direction = 1 if rng.random()<.5 else -1
        car=spawn(track, rng.uniform(30., track.perimeter-30.), direction,
                  rng.uniform(-18., 18.), rng.uniform(-.45, .45), rng.uniform(.8, 1.2))
        xs.append(inputs(track,car,mode)); ys.append(teacher(track,car))
    return xs, ys


def fit(net, xs, ys, epochs, rng):
    """Mini-batch Adam on tanh MLP, stored in the shared NeuralNetwork format."""
    x=np.asarray(xs); y=np.asarray(ys); matrices=[]; offset=0
    for a,b in zip(net.architecture, net.architecture[1:]):
        count=(a+1)*b
        matrices.append(np.asarray(net.weights[offset:offset+count]).reshape(b,a+1).copy()); offset+=count
    m=[np.zeros_like(w) for w in matrices]; v=[np.zeros_like(w) for w in matrices]; step=0
    for epoch in range(epochs):
        order=rng.permutation(len(x))
        for start in range(0,len(x),256):
            indices=order[start:start+256]; activations=[x[indices]]
            for w in matrices: activations.append(np.tanh(activations[-1]@w[:,:-1].T+w[:,-1]))
            delta=2*(activations[-1]-y[indices])/len(indices)
            gradients=[]
            for layer in range(len(matrices)-1,-1,-1):
                delta=delta*(1-activations[layer+1]**2)
                gradients.append(np.column_stack((delta.T@activations[layer], delta.sum(axis=0))))
                delta=delta@matrices[layer][:,:-1]
            step+=1
            for i,g in enumerate(reversed(gradients)):
                m[i]=.9*m[i]+.1*g; v[i]=.999*v[i]+.001*g*g
                matrices[i]-=.001*(m[i]/(1-.9**step))/(np.sqrt(v[i]/(1-.999**step))+1e-8)
    net.weights=np.concatenate([w.ravel() for w in matrices]).tolist()
    return float(np.mean((np.asarray(net.forward_batch(xs))-y)**2))


def rollout(net, track, mode, direction, lateral=0., angle=0., factor=1., collect=False):
    use_track(track)
    car=spawn(track, 30. if direction>0 else track.perimeter-30., direction, lateral, angle, factor)
    xs,ys=[],[]; steps=0; penalty=0.
    for steps in range(math.ceil(track.perimeter/(1.8*factor)*1.5)):
        observation=inputs(track,car,mode)
        if collect and steps%3==0:
            xs.append(observation);ys.append(teacher(track,car))
        out=net.forward(observation)
        reward,_=app.step([car],[],controls=[(out[0],(out[1]+1)/2,0.)]);penalty+=reward
        if car['crashed'] or car.get('finished'):break
    return dict(track=track.name,direction=direction,lateral=lateral,angle=angle,speed_factor=factor,
                finished=bool(car.get('finished')),crashed=car['crashed'],steps=steps+1,
                progress=max(0.,min(1.,car['travel']/(track.perimeter-30.))),penalty=penalty),xs,ys


def evaluate(net, tracks, mode):
    rows=[]
    for track in tracks:
        for direction in (-1,1):
            for lateral,angle,factor in ((0.,0.,1.),(-8.,.12,.8),(8.,-.12,1.2)):
                row,_,_=rollout(net,track,mode,direction,lateral,angle,factor); rows.append(row)
    return dict(completed=sum(r['finished'] for r in rows),attempts=len(rows),
                mean_progress=sum(r['progress'] for r in rows)/len(rows),rows=rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('games/car/models/turn_specialists'))
    parser.add_argument('--samples',type=int,default=8000)
    parser.add_argument('--epochs',type=int,default=180)
    parser.add_argument('--rounds',type=int,default=4)
    parser.add_argument('--seed',type=int,default=20261111)
    parser.add_argument('--mode',choices=(*MODES,'both'),default='both')
    args=parser.parse_args()
    if min(args.samples,args.epochs,args.rounds)<1:parser.error('Training budgets must be positive')
    args.output.mkdir(parents=True,exist_ok=True)
    tracks=[Track.generate(n) for n in ('tight_turns','tight_turns_mirrored')]
    for track in tracks:track.set_backend('rust')
    holdout=[Track([(x*scale,y*scale,z) for x,y,z in tracks[0].points],half_width=width,
                   name=f'holdout_turns_{scale}_{width}',closed=False)
             for scale,width in ((.9,34.),(1.1,42.))]
    for mode in MODES if args.mode=='both' else (args.mode,):
        rng=np.random.default_rng(args.seed)
        net=NeuralNetwork([INPUT_COUNTS[mode],48,32,2],seed=args.seed).set_backend('rust')
        weights=[]
        for a,b in zip(net.architecture,net.architecture[1:]):
            w=rng.normal(0.,1/math.sqrt(a),(b,a+1)); w[:,-1]=0.;weights.extend(w.ravel())
        net.weights=list(map(float,weights))
        net.metadata=dict(radar_mode=mode,track='tight_turns',traffic='convoy',radar_scale=2.,sensor_version=1,
            experiment=dict(road_only=True,steering_boost=1.,brake_max_reduction=.5,
                            method='imitation_then_dagger',training_tracks=[t.name for t in tracks],
                            samples=args.samples,epochs=args.epochs,rounds=args.rounds,generations=args.rounds),
            scenario=dict(seed=args.seed,generation=1,car_count=5,training_count=5,cones=[],
                          direction=1,direction_label='forward',track='tight_turns',start_mode='standard'))
        baseline=evaluate(net,holdout,mode)
        print(json.dumps(dict(mode=mode,phase='sampling',baseline_completed=baseline['completed'])),flush=True)
        xs,ys=sample_data(tracks,mode,args.samples,rng)
        best=None; best_key=None; best_round=None; history=[]
        for round_index in range(args.rounds):
            loss=fit(net,xs,ys,args.epochs,rng)
            training=evaluate(net,tracks,mode)
            key=(training['completed'],training['mean_progress'])
            history.append(dict(round=round_index+1,loss=loss,completed=training['completed'],
                                attempts=training['attempts'],mean_progress=training['mean_progress'],samples=len(xs)))
            print(json.dumps(dict(mode=mode,**history[-1])),flush=True)
            if best_key is None or key>best_key:best_key=key;best=net.weights[:];best_round=round_index+1
            net.generation=round_index+1; net.history=history[:]; net.score=training['mean_progress']
            net.save(args.output/f'{mode}_latest.json')
            if round_index+1 == args.rounds: break
            for track in tracks:
                for direction in (-1,1):
                    for lateral in (-12.,0.,12.):
                        _,new_x,new_y=rollout(net,track,mode,direction,lateral,collect=True)
                        xs.extend(new_x);ys.extend(new_y)
        net.weights=best
        net.metadata['selected_round']=best_round
        training=evaluate(net,tracks,mode);validation=evaluate(net,holdout,mode)
        net.score=training['mean_progress'];net.metadata['turn_validation']=dict(completed=validation['completed'],attempts=validation['attempts'])
        net.save(args.output/f'{mode}.json')
        report=dict(mode=mode,seed=args.seed,selected_round=best_round,training=training,holdout=validation,untrained_holdout=baseline,history=history,
                    selection='training completion and progress only; holdout never used for selection',
                    limitations=['Flat road-edge reflections only; no floor echoes, traffic or hill training.',
                                 'Echo returns are idealized reflection paths, not acoustic return-to-receiver simulation.'])
        (args.output/f'{mode}_report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(mode=mode,phase='done',training_completed=training['completed'],
                             holdout_completed=validation['completed'],holdout_attempts=validation['attempts'])),flush=True)


if __name__=='__main__':main()
