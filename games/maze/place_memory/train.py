import argparse
from collections import Counter
import json
from pathlib import Path
import random
import mlx.core as mx
import mlx.nn as nn
from ..junction.model import JunctionDetector
from ..modular.train import make_update,write_json
from .network import PlaceMemory
from .task import make_places,sample_sequence,signatures,sample_headings


def prepare_pool(detector,seed,count,size=21):
    pool=[make_places(seed+i,size) for i in range(count)]
    rows=[row for places in pool for poses in places['oriented_detector_readings'] for row in poses]
    gates=(detector(mx.array(rows))>.5).tolist();offset=0
    for places in pool:
        n=len(places['points']);places['gates']=[gates[offset+i*4:offset+(i+1)*4] for i in range(n)];offset+=n*4
    return pool


def batch(pool,length,count,rng,balanced=True):
    xs=[];ys=[];writes=[]
    for _ in range(count):
        places=rng.choice(pool);ids,labels=sample_sequence(places,length,rng,balanced=balanced)
        headings=sample_headings(length,rng)
        xs.append([places['oriented_readings'][i][h] for i,h in zip(ids,headings)]);ys.append(labels)
        writes.append([places['gates'][i][h] for i,h in zip(ids,headings)])
    return mx.array(xs),mx.array(writes),mx.array(ys)


def metrics(logits,y):
    pred=logits>0;truth=y>.5
    tp=int(mx.sum(pred&truth));fp=int(mx.sum(pred&~truth));fn=int(mx.sum(~pred&truth));tn=int(mx.sum(~pred&~truth))
    total=tp+fp+fn+tn
    return dict(accuracy=(tp+tn)/total,balanced_accuracy=.5*(tp/max(1,tp+fn)+tn/max(1,tn+fp)),
                seen_recall=tp/max(1,tp+fn),unseen_recall=tn/max(1,tn+fp),
                seen_precision=tp/max(1,tp+fp),tp=tp,fp=fp,fn=fn,tn=tn,
                mean_reward=(tp+tn-fp-fn)/total,
                always_new_accuracy=(tn+fp)/total,always_seen_accuracy=(tp+fn)/total)


def evaluate(model,pool,balanced=True):
    results={}
    for length in (10,20,40,67):
        x,g,y=batch(pool,length,128,random.Random(990000+length),balanced)
        logits=model(x,g);mx.eval(logits)
        base=model(x,g,True);mx.eval(base)
        shuffled=model(x,g,shuffle_read=True);mx.eval(shuffled)
        results[str(length)]=dict(normal=metrics(logits,y),memory_reset=metrics(base,y),history_from_other_trial=metrics(shuffled,y),
                                 samples=128,events=length)
    ambiguous=total=0
    for places in pool:
        counts=Counter(signatures(places))
        ambiguous+=sum(n for n in counts.values() if n>1);total+=sum(counts.values())
    return dict(by_length=results,indistinguishable_locations=ambiguous,total_locations=total,
                detector_write_rate=sum(sum(sum(poses) for poses in p['gates']) for p in pool)/(total*4))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=Path('games/maze/models/place_memory_v2'))
    p.add_argument('--updates',type=int,default=1200)
    p.add_argument('--sampling',choices=['balanced','uniform'],default='balanced')
    p.add_argument('--maze-size',type=int,default=21)
    p.add_argument('--resume-from',type=Path)
    args=p.parse_args()
    if args.updates<1:raise ValueError('updates must be positive')
    balanced=args.sampling=='balanced'
    if args.output.exists():raise ValueError('Use a new experiment directory')
    args.output.mkdir(parents=True)
    mx.set_default_device(mx.gpu);mx.random.seed(73)
    detector=JunctionDetector()
    detector.load_weights(str(args.resume_from/'detector.safetensors') if args.resume_from else 'games/maze/models/junction_detector_v1/detector.safetensors')
    detector.save_weights(str(args.output/'detector.safetensors'))
    pool=prepare_pool(detector,40000000,256,args.maze_size)
    model=PlaceMemory()
    previous_updates=0
    if args.resume_from:
        model.load_weights(str(args.resume_from/'memory.safetensors'))
        old=json.loads((args.resume_from/'report.json').read_text())
        previous_updates=old.get('total_updates',max((e['update'] for e in old['history']),default=0))
    # Persist exact starting weights as evidence of warm start.
    model.save_weights(str(args.output/'initial_memory.safetensors'))
    # Correct classification yields +1, wrong classification -1. Cross-entropy
    # supplies a stable training signal for that binary decision (not a reward input).
    update=make_update(model,lambda m,x,g,y:nn.losses.binary_cross_entropy(m(x,g),y,with_logits=True,reduction='mean'),.001)
    report=dict(experiment='teleport_place_memory',phase='training',hidden=256,seed=73,
                pose='independent random cardinal heading at every placement',inputs='8 ray distances only; no coordinates or movement',
                read_before_write=True,rewards=dict(correct=1,incorrect=-1),optimizer='Adam / binary cross entropy',
                maze_size=args.maze_size,sampling=args.sampling,training_mazes=256,history=[],previous_updates=previous_updates,total_updates=previous_updates,
                resumed_from=str(args.resume_from) if args.resume_from else None,optimizer_state='fresh Adam; trained network weights retained')
    write_json(args.output/'report.json',report)
    rng=random.Random(73)
    for i in range(args.updates):
        length=(10,20,40,67)[min(3,i*4//args.updates)]
        x,g,y=batch(pool,length,32,rng,balanced)
        loss=update(x,g,y);mx.eval(loss,model.parameters())
        if (i+1)%100==0:
            report['total_updates']=previous_updates+i+1
            item=dict(update=i+1,length=length,loss=float(loss));report['history'].append(item)
            write_json(args.output/'report.json',report);print('TRAIN',json.dumps(item),flush=True)
    model.save_weights(str(args.output/'memory.safetensors'))
    report['phase']='evaluation';write_json(args.output/'report.json',report)
    report['test']=evaluate(model,prepare_pool(detector,89000000,128,args.maze_size),balanced)
    report['phase']='complete';write_json(args.output/'report.json',report)
    print('RESULT',json.dumps(report['test']),flush=True)


if __name__=='__main__':main()
