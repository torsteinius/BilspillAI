"""Train detector on observations from a frozen walking policy using stop rewards."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import mlx.core as mx
from ..training import Trainer
from ..generator import generate
from ..modular.train import make_update,write_json
from .model import JunctionDetector
from .task import walk,is_landmark,stop_reward


def evaluate(detector,walker,count=300):
    samples=[]
    for i in range(count):
        size=(5,9,15)[i%3]
        sequence,_=walk(walker,generate(size,size,seed=92000000+i))
        samples.extend(sequence)
    probabilities=detector(mx.array([s['rays'] for s in samples])).tolist()
    counts=Counter();by_kind={}
    for s,p in zip(samples,probabilities):
        stop=p>.5;truth=is_landmark(s['kind'])
        counts['tp' if stop and truth else 'fp' if stop else 'fn' if truth else 'tn']+=1
        k=by_kind.setdefault(s['kind'],dict(observations=0,signals=0))
        k['observations']+=1;k['signals']+=int(stop)
    tp,fp,fn,tn=[counts[k] for k in ('tp','fp','fn','tn')]
    return dict(mazes=count,observations=len(samples),true_stops=tp,false_stops=fp,
                missed_landmarks=fn,correct_silence=tn,precision=tp/max(1,tp+fp),
                recall=tp/max(1,tp+fn),mean_reward=(tp-fp)/len(samples),by_kind=by_kind)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--walker',type=Path,default=Path('games/maze/models/learned_memory_40_three_layers.json'))
    p.add_argument('--output',type=Path,default=Path('games/maze/models/junction_detector_v1'))
    p.add_argument('--rounds',type=int,default=160)
    args=p.parse_args()
    if args.rounds<1:raise ValueError('rounds must be positive')
    if args.output.exists():raise ValueError('Use a new output directory')
    args.output.mkdir(parents=True)
    mx.set_default_device(mx.gpu);mx.random.seed(57)
    walker=Trainer.load(args.walker)
    # Freeze an independent checkpoint so future changes cannot alter this task.
    walker.network.save(args.output/'walker.json')
    frozen=walker.network.weights[:]
    digest=hashlib.sha256(json.dumps(frozen).encode()).hexdigest()
    detector=JunctionDetector()
    # Exact expected reward of the binary stop action. No stop has reward zero.
    # p(stop)*reward(stop) is differentiable; there is no reward for silence.
    update=make_update(detector,lambda m,x,reward:-mx.mean(m(x)*reward),.003)
    report=dict(experiment='junction_detector_v1',walker_generation=walker.network.generation,
                walker_weights_sha256=digest,architecture=[8,32,16,1],backend='Apple Metal GPU',
                definition='branches (3+ open neighbours) and corners (2 non-opposite neighbours)',
                rewards=dict(correct_stop=1,false_stop=-1,no_stop=0),phase='training',training=[])
    write_json(args.output/'report.json',report)
    seen=0
    for iteration in range(args.rounds):
        samples=[]
        for j in range(8):
            index=iteration*8+j;size=(5,9,15)[index%3]
            sequence,_=walk(walker,generate(size,size,seed=31000000+index))
            samples.extend(sequence)
        x=mx.array([s['rays'] for s in samples]);r=mx.array([stop_reward(True,s['kind']) for s in samples])
        for _ in range(10):
            ids=mx.random.randint(0,len(samples),(128,))
            loss=update(x[ids],r[ids]);mx.eval(loss,detector.parameters())
        seen+=len(samples)
        if (iteration+1)%20==0 or iteration+1==args.rounds:
            entry=dict(round=iteration+1,observations_seen=seen,expected_reward=-float(loss))
            report['training'].append(entry)
            write_json(args.output/'report.json',report)
            print('TRAIN',json.dumps(entry),flush=True)
    assert frozen==walker.network.weights
    detector.save_weights(str(args.output/'detector.safetensors'))
    report.update(phase='complete',test=evaluate(detector,walker),training_mazes=args.rounds*8,
                  observations_seen=seen,walker_unchanged=True)
    write_json(args.output/'report.json',report)
    print('RESULT',json.dumps(report['test']),flush=True)


if __name__=='__main__':main()
