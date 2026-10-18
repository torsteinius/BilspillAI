"""Assisted evolution: exact next-action matches are the ONLY fitness signal.

Samples are independent route points with their complete recorded landmark history.
No episode rollout, game reward, partial-bit credit, or validation-based selection.
"""
import argparse
import copy
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import time
import uuid

from ai.network import NeuralNetwork
from ai_service.client import Client
from games.maze.history import decode_bits, widen_network

BITS = {'backward': (0,0), 'right': (0,1), 'left': (1,0), 'forward': (1,1)}


@dataclass(frozen=True)
class Point:
    values: tuple
    action: str
    route_id: str
    attempt: int
    step: int
    size: str

    def inputs(self, width):
        if len(self.values) > width:
            raise ValueError('History exceeds input capacity')
        return list(self.values) + [0.]*(width-len(self.values))


def match_reward(outputs, expected_action):
    if expected_action not in BITS:
        raise ValueError('Unknown demonstrated action')
    return 1. if decode_bits(outputs) == expected_action else -1.


def load_points(dataset):
    dataset=Path(dataset)
    manifest=json.loads((dataset/'manifest.json').read_text())
    if manifest['status']!='complete' or manifest['student_output_encoding']!='bits2':
        raise ValueError('Expected a complete two-bit demonstration dataset')
    routes=defaultdict(list);validation=[];sets={'train':set(),'validation':set()}
    counts=Counter()
    with (dataset/'successful-routes.jsonl').open() as stream:
        for line in stream:
            route=json.loads(line)
            if not route['escaped']:
                raise ValueError('Failed route in demonstration file')
            split=route['split'];sets[split].add(route['route_id'])
            size=f"{route['width']}x{route['height']}"; points=[]
            for sample in route['samples']:
                width=4*(1+sample['history_count'])
                observation=sample['observation']
                if width>len(observation) or any(observation[width:]):
                    raise ValueError('Invalid memory occupancy or padding')
                if tuple(sample['target_bits']) != BITS[sample['action']]:
                    raise ValueError('Route action and target bits disagree')
                points.append(Point(tuple(observation[:width]),sample['action'],route['route_id'],
                                    route['attempt'],sample['step'],size))
            counts[split]+=len(points)
            if split=='train':routes[size].append(points)
            else:validation.extend(points)
    if sets['train'] & sets['validation']:
        raise ValueError('Training/validation wall layouts overlap')
    if dict(counts)!=manifest['split_samples']:
        raise ValueError('Sample counts differ from manifest')
    if not routes or not validation:
        raise ValueError('Both training and validation data are required')
    return manifest, dict(routes), validation


def sample_batch(routes, rng, count):
    # Balance sizes, then select a route and an arbitrary point on that route.
    sizes=sorted(routes);offset=rng.randrange(len(sizes));points=[]
    for i in range(count):
        route=rng.choice(routes[sizes[(offset+i)%len(sizes)]])
        points.append(rng.choice(route))
    rng.shuffle(points)
    return points


def train_round(client, session_id, points, width, generation):
    asked=client.ask(session_id,f'ask-{generation}')
    candidates=asked['candidate_ids']
    reply=client.candidate_predict(session_id,asked['generation_id'],[
        dict(candidate_id=cid,sample_id=str(i),input=point.inputs(width))
        for cid in candidates for i,point in enumerate(points)])
    if reply.get('backend')!='mlx-gpu':raise RuntimeError('GPU inference not confirmed')
    returned={(r['candidate_id'],r['sample_id']):r['output'] for r in reply['items']}
    expected={(cid,str(i)) for cid in candidates for i in range(len(points))}
    if len(reply['items'])!=len(expected) or set(returned)!=expected:
        raise ValueError('Prediction identifiers do not match sampled points')
    scores=[sum(match_reward(returned[cid,str(i)],point.action) for i,point in enumerate(points))/len(points)
            for cid in candidates]
    used=max(len(p.values) for p in points)
    result=client.tell(session_id,asked['generation_id'],scores,f'tell-{generation}',
        f'route-points-{generation}',used_inputs=[i<used for i in range(width)])
    winner=candidates.index(result['selected_candidate'])
    if abs(result['score']-scores[winner])>1e-9:raise RuntimeError('Saved fitness differs from route matches')
    return dict(round=generation,fitness=scores,accuracies=[(s+1)/2 for s in scores],
        selected=winner,checkpoint_id=result['checkpoint_id'],
        selected_accuracy=(scores[winner]+1)/2,
        samples=[dict(attempt=p.attempt,step=p.step,route_id=p.route_id,size=p.size,
                      history_count=len(p.values)//4-1,target=p.action) for p in points])


def evaluate(client,network_id,points,width):
    correct=0; by_size=defaultdict(Counter);by_action=defaultdict(Counter);predicted=Counter()
    checkpoint=None
    for start in range(0,len(points),128):
        batch=points[start:start+128]
        reply=client.predict(network_id,[p.inputs(width) for p in batch])
        checkpoint=checkpoint or reply['checkpoint_id']
        if reply['checkpoint_id']!=checkpoint or len(reply['outputs'])!=len(batch):
            raise RuntimeError('Checkpoint changed or evaluation response incomplete')
        for p,out in zip(batch,reply['outputs']):
            ok=match_reward(out,p.action)==1;correct+=ok;predicted[decode_bits(out)]+=1
            for group in (by_size[p.size],by_action[p.action]):
                group['count']+=1;group['correct']+=ok
    def stats(groups):return {k:dict(v,accuracy=v['correct']/v['count']) for k,v in groups.items()}
    labels=Counter(p.action for p in points)
    return dict(points=len(points),correct=correct,accuracy=correct/len(points),
        mean_reward=2*correct/len(points)-1,by_size=stats(by_size),by_action=stats(by_action),
        predicted_actions=dict(predicted),target_actions=dict(labels),
        majority_action_baseline=max(labels.values())/len(points),checkpoint_id=checkpoint)


def prepare_model(source,dataset_manifest):
    source=copy.deepcopy(source)
    old=NeuralNetwork(source['architecture'],seed=source['seed'])
    old.weights=source['weights'];old.generation=source['generation'];old.history=source.get('history',[])
    old.metadata={k:v for k,v in source.items() if k not in ('architecture','weights','generation','history','seed','score','format_version')}
    config=old.metadata['config']
    for key,value in [('history_sensor_count',4),('history_output_encoding','bits2'),
                      ('history_memory_decay',dataset_manifest['student_memory_decay']),
                      ('history_memory_floor',dataset_manifest['student_memory_floor']),
                      ('history_newest_first',dataset_manifest['student_newest_first'])]:
        if config.get(key)!=value:raise ValueError(f'Source/dataset mismatch: {key}')
    width=dataset_manifest['student_input_count']
    model=widen_network(old,[width,*old.architecture[1:]])
    model.metadata['history_hidden_widths']=list(model.architecture[1:-1])
    active=old.metadata.get('mutation_active_inputs',[True]*old.architecture[0])
    model.metadata['mutation_active_inputs']=active+[False]*(width-old.architecture[0])
    dimensions=max(dataset_manifest['dimensions'],key=lambda d:(d[0]-2)*(d[1]-2))
    model.metadata['curriculum'].update(width=dimensions[0],height=dimensions[1],streak=0,streak_model=None)
    model.metadata['training_objective']=dict(name='recorded_next_action_match_v1',
        correct=1,incorrect=-1,aggregation='mean over same sampled points for all candidates',
        other_rewards=False,history='full recorded history at randomly sampled route point',
        method='evolution',source_generation=old.generation)
    return model


def run(args):
    if min(args.rounds,args.batch_size,args.population)<1 or args.sigma<=0:
        raise ValueError('Positive training settings required')
    dataset=Path(args.dataset);output=Path(args.output)
    manifest,routes,validation=load_points(dataset)
    client=Client(args.service,timeout=120)
    if client.engine_status().get('backend')!='mlx-gpu':raise RuntimeError('GPU service required')
    source=client.checkpoint(args.source_network)
    model=prepare_model(source['checkpoint'],manifest)
    output.mkdir(parents=True,exist_ok=False)
    initial=output/'initial.json';model.save(initial)
    (output/'source.json').write_text(json.dumps(source['checkpoint']))
    network_id='route-match-'+uuid.uuid4().hex[:12]
    client.import_legacy(network_id,str(initial.resolve()))
    state=dict(status='running',network_id=network_id,source_network=args.source_network,
        source_checkpoint_id=source['checkpoint_id'],source_generation=model.generation,
        architecture=list(model.architecture),dataset=str(dataset.resolve()),
        dataset_manifest_sha256=hashlib.sha256((dataset/'manifest.json').read_bytes()).hexdigest(),
        rounds=args.rounds,completed_rounds=0,batch_size=args.batch_size,population=args.population,
        mutation_sigma=args.sigma,seed=args.seed,reward=model.metadata['training_objective'])
    started=time.perf_counter()
    def save():
        state['elapsed_seconds']=time.perf_counter()-started
        temporary=output/'state.tmp';temporary.write_text(json.dumps(state,indent=2));temporary.replace(output/'state.json')
    save()
    try:
        state['before']=evaluate(client,network_id,validation,model.architecture[0]);save()
        session=client.create_evolution_session(network_id=network_id,population_size=args.population,
            elite_count=1,mutation_sigma=args.sigma,seed=args.seed,request_id=uuid.uuid4().hex)['session_id']
        state['session_id']=session;rng=random.Random(args.seed)
        with (output/'rounds.jsonl').open('w') as log:
            for generation in range(1,args.rounds+1):
                batch=sample_batch(routes,rng,args.batch_size)
                record=train_round(client,session,batch,model.architecture[0],generation)
                log.write(json.dumps(record)+'\n');log.flush()
                state.update(completed_rounds=generation,last_batch_accuracy=record['selected_accuracy'],
                             checkpoint_id=record['checkpoint_id']);save()
                if generation%10==0:print(json.dumps({k:state[k] for k in ('completed_rounds','last_batch_accuracy','elapsed_seconds')}),flush=True)
        state['after']=evaluate(client,network_id,validation,model.architecture[0])
        final=client.checkpoint(network_id)
        (output/'final.json').write_text(json.dumps(final['checkpoint'],indent=2))
        state.update(status='complete',final_model_generation=final['checkpoint']['generation'],
            checkpoint_id=final['checkpoint_id'],source_unchanged=client.checkpoint(args.source_network)['checkpoint_id']==source['checkpoint_id'])
        if not state['source_unchanged']:raise RuntimeError('Source model changed during separate experiment')
        save();print(json.dumps(state),flush=True)
    except Exception as error:
        state.update(status='error',error=str(error));save();raise
    finally:client.close()
    return state


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--service',default='http://127.0.0.1:8787')
    p.add_argument('--source-network',default='history-4rays-decay75-v1')
    p.add_argument('--rounds',type=int,default=200);p.add_argument('--batch-size',type=int,default=128)
    p.add_argument('--population',type=int,default=4);p.add_argument('--sigma',type=float,default=.03)
    p.add_argument('--seed',type=int,default=20261018)
    run(p.parse_args())


if __name__=='__main__':main()
