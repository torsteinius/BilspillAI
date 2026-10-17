"""Train and measure three networks on Metal, saving honest stage-by-stage reports."""
from functools import partial
import argparse
import json
from pathlib import Path
import random
import time
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from ..generator import generate
from .networks import Perception, Memory, Decision, HIDDEN
from .tasks import rays_at, labels_at, synthetic_batch, World


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    temporary.replace(path)


def make_update(model, loss_fn, learning_rate=.002):
    optimizer = optim.Adam(learning_rate=learning_rate)
    grad_fn = nn.value_and_grad(model, loss_fn)
    @partial(mx.compile, inputs=[model.state, optimizer.state], outputs=[model.state, optimizer.state])
    def update(*args):
        loss, grads = grad_fn(model, *args)
        grads, _ = optim.clip_grad_norm(grads, 1.)
        optimizer.update(model, grads)
        return loss
    return update


def perception_data(seed, count):
    rng = random.Random(seed)
    rays, labels = [], []
    for i in range(count):
        maze = generate(15, 15, seed=seed+i)
        floors = [(x,y) for y,row in enumerate(maze.rows) for x,c in enumerate(row) if c=='.']
        for _ in range(32):
            x,y = rng.choice(floors)
            h = rng.randrange(4)
            rays.append(rays_at(maze,x,y,h))
            labels.append(labels_at(maze,x,y,h))
    return mx.array(rays), mx.array(labels)


def train_perception(model, steps):
    x,y=perception_data(10000,160)
    update=make_update(model,lambda m,a,b:mx.mean((m(a)-b)**2))
    for i in range(steps):
        ids=mx.random.randint(0,len(x),(128,))
        loss=update(x[ids],y[ids]);mx.eval(loss,model.parameters())
    tx,ty=perception_data(9000000,40)
    out=model(tx)
    return dict(open_accuracy=float(mx.mean((out[:,:4]>.5)==(ty[:,:4]>.5))),
                length_mae=float(mx.mean(mx.abs(out[:,4:]-ty[:,4:]))),samples=len(tx))


def train_memory(model, steps, output, report):
    def loss_fn(m, x, labels):
        h,c=m(x)
        return nn.losses.cross_entropy(m.recall_logits(h[:,-1,:])[:,:labels.shape[1]],labels,reduction='mean')
    update=make_update(model,loss_fn,.001)
    results=[]
    for length in (5,10,20,40,67):
        start=time.monotonic()
        for i in range(steps):
            # Rehearse shorter horizons to reduce forgetting during curriculum.
            shorter=[k for k in (5,10,20,40,67) if k<length]
            train_length=shorter[(i//5)%len(shorter)] if shorter and i%5==0 else length
            x,y=synthetic_batch(train_length,32,100000+length*10000+i)
            loss=update(mx.array(x),mx.array(y));mx.eval(loss,model.parameters())
        result=test_memory(model,length)
        result['seconds']=time.monotonic()-start
        results.append(result)
        report.update(phase='memory',memory_curriculum=results)
        write_json(output/'report.json',report)
        model.save_weights(str(output/'memory.safetensors'))
        print('MEMORY',json.dumps(result),flush=True)
    return results


def test_memory(model,length):
    x,y=synthetic_batch(length,256,80000000+length)
    h,c=model(mx.array(x))
    predicted=mx.argmax(model.recall_logits(h[:,-1,:])[:,:length],axis=-1)
    hits=predicted==mx.array(y)
    return dict(length=length,accuracy=float(mx.mean(hits)),chance=.25,
                exact_sequence_accuracy=float(mx.mean(mx.all(hits,axis=-1))),
                queried_positions={str(i+1):float(mx.mean(hits[:,i])) for i in (0,min(2,length-1),length//2,length-1)},
                samples=256)


def observe_batch(perception, memory, worlds, h,c):
    rays=mx.array([w.observe() for w in worlds])
    perceived=perception(rays)
    previous=mx.array([w.previous for w in worlds])
    motion=mx.array([w.motion for w in worlds])
    events=mx.concatenate([perceived,previous,motion],axis=-1)
    # Every movement observation is an event in this first prototype. This
    # avoids silently losing corridor displacement between junctions.
    hs,cs=memory(events[:,None,:],h,c)
    h,c=hs[:,0,:],cs[:,0,:]
    mx.eval(rays,perceived,previous,h,c)
    return rays,perceived,previous,h,c


def train_decision(perception,memory,decision,iterations,output,report):
    # Frozen perception and LSTM; policy gradient updates only the decision net.
    def loss_fn(m,rays,seen,h,prev,actions,advantages):
        logits=m(rays,seen,h,prev)
        logp=logits-mx.logsumexp(logits,axis=-1,keepdims=True)
        selected=mx.take_along_axis(logp,actions[:,None],axis=-1)[:,0]
        entropy=-mx.sum(mx.exp(logp)*logp,axis=-1)
        return -mx.mean(selected*advantages+.02*entropy)
    update=make_update(decision,loss_fn,.001)
    metrics=[]
    for iteration in range(iterations):
        size=5 if iteration<iterations//3 else 9 if iteration<2*iterations//3 else 15
        worlds=[World(generate(size,size,seed=20000000+iteration*32+i)) for i in range(32)]
        h=mx.zeros((32,HIDDEN));c=mx.zeros_like(h)
        records=[];rewards=[];masks=[]
        for step in range(96):
            rays,seen,prev,h,c=observe_batch(perception,memory,worlds,h,c)
            logits=decision(rays,seen,h,prev)
            actions=mx.random.categorical(logits)
            choices=actions.tolist()
            active=[not w.escaped for w in worlds]
            reward=[w.step(a) if ok else 0. for w,a,ok in zip(worlds,choices,active)]
            records.append((rays,seen,h,prev,actions))
            rewards.append(reward);masks.append(active)
            if not any(not w.escaped for w in worlds):break
        # Discounted returns with a per-timestep baseline over environments.
        returns=[];running=[0.]*32
        for reward in reversed(rewards):
            running=[r+.97*v for r,v in zip(reward,running)]
            returns.append(running)
        returns=mx.array(list(reversed(returns)))
        mask=mx.array(masks)
        baseline=mx.sum(returns*mask,axis=1,keepdims=True)/mx.maximum(1,mx.sum(mask,axis=1,keepdims=True))
        advantage=(returns-baseline)*mask
        advantage=advantage/(mx.sqrt(mx.mean(advantage**2))+1e-6)
        args=[mx.concatenate([record[j] for record in records],axis=0) for j in range(5)]
        loss=update(*args,advantage.reshape(-1));mx.eval(loss,decision.parameters())
        if (iteration+1)%10==0 or iteration==iterations-1:
            item=dict(iteration=iteration+1,size=size,training_escape_rate=sum(w.escaped for w in worlds)/32,
                      mean_visited=sum(len(w.visits) for w in worlds)/32,loss=float(loss))
            metrics.append(item)
            report.update(phase='decision',decision_training=metrics)
            write_json(output/'report.json',report)
            decision.save_weights(str(output/'decision.safetensors'))
            print('DECISION',json.dumps(item),flush=True)
    return metrics


def rollout(perception,memory,decision,maze,zero_memory=False,record=False,max_steps=256):
    world=World(maze);h=mx.zeros((1,HIDDEN));c=mx.zeros_like(h)
    frames=[world.frame()] if record else []
    for step in range(max_steps):
        rays,seen,prev,h,c=observe_batch(perception,memory,[world],h,c)
        used=mx.zeros_like(h) if zero_memory else h
        action=int(mx.argmax(decision(rays,seen,used,prev)[0]))
        world.step(action)
        if record:frames.append(world.frame(action,step+1,float(mx.sqrt(mx.mean(h*h)))))
        if world.escaped:break
    return world,frames


def evaluate(perception,memory,decision,count=40):
    results={}
    for size in (5,9,15):
        for zero in (False,True):
            worlds=[rollout(perception,memory,decision,generate(size,size,seed=70000000+size*10000+i),zero)[0] for i in range(count)]
            results[f'{size}x{size}_'+('memory_zeroed' if zero else 'memory')]=dict(
                samples=count,escape_rate=sum(w.escaped for w in worlds)/count,
                mean_visited=sum(len(w.visits) for w in worlds)/count,
                mean_collisions=sum(w.collisions for w in worlds)/count)
    return results


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=Path('games/maze/models/modular_lstm_v1'))
    parser.add_argument('--memory-steps',type=int,default=150)
    parser.add_argument('--policy-iterations',type=int,default=120)
    parser.add_argument('--perception-steps',type=int,default=500)
    parser.add_argument('--phase',choices=['all','components','decision'],default='all')
    args=parser.parse_args()
    mx.set_default_device(mx.gpu)
    if not mx.metal.is_available():raise RuntimeError('Metal GPU required')
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'report.json').exists() and args.phase!='decision':
        raise ValueError('Choose a new output directory; refusing to overwrite an experiment')
    mx.random.seed(42)
    perception,memory,decision=Perception(),Memory(),Decision()
    report=dict(experiment='modular_lstm_v1',hidden_size=HIDDEN,memory_state_values=2*HIDDEN,
                backend='Apple Metal / MLX',event_definition='every movement observation',
                goal='find exit and explore unseen cells',phase='perception',seed=42)
    if args.phase!='decision':
        write_json(args.output/'report.json',report)
        report['perception']=train_perception(perception,args.perception_steps)
        perception.save_weights(str(args.output/'perception.safetensors'))
        print('PERCEPTION',report['perception'],flush=True)
        train_memory(memory,args.memory_steps,args.output,report)
        report['memory_final_tests']=[test_memory(memory,k) for k in (5,10,20,40,67)]
        report['phase']='components_complete';write_json(args.output/'report.json',report)
    else:
        report=json.loads((args.output/'report.json').read_text())
        perception.load_weights(str(args.output/'perception.safetensors'))
        memory.load_weights(str(args.output/'memory.safetensors'))
    if args.phase!='components':
        train_decision(perception,memory,decision,args.policy_iterations,args.output,report)
        report['phase']='evaluation';write_json(args.output/'report.json',report)
        report['navigation_tests']=evaluate(perception,memory,decision)
        report['phase']='complete';write_json(args.output/'report.json',report)
        print('FINAL',json.dumps(report['navigation_tests']),flush=True)


if __name__=='__main__':main()
