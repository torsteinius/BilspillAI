"""Fresh action-history model trained on actual episode rewards, not route labels."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import random
import time

from ai_service.generic import MLXDenseBackend, EvolutionSession
from games.maze.training import Trainer
from games.maze.world import Maze
from scripts.add_route_choice_memory import fresh_action_model


def maze_sets(dataset):
    result={'train':{},'validation':{}}
    with (Path(dataset)/'successful-routes.jsonl').open() as stream:
        for line in stream:
            route=json.loads(line);m=route['maze']
            key=(tuple(m['rows']),tuple(m['start']),m['heading'])
            result[route['split']][key]=Maze(m['name'],tuple(m['rows']),tuple(m['start']),m['heading'])
    return {k:list(v.values()) for k,v in result.items()}


def rollout(backend,trainer,populations,mazes):
    layers=backend.prepare(trainer.network.architecture,populations)
    episodes=[[trainer.make_episode(m) for m in mazes] for _ in populations]
    used=[4]*len(populations)
    while True:
        active=[(i,e) for i,row in enumerate(episodes) for e in row if not e.done]
        if not active:break
        for i,e in active:used[i]=max(used[i],4+e.memory_row_width*len(e.memory))
        outputs,_=backend.predict_indexed(layers,[i for i,e in active],[e.observations() for i,e in active],
                                         normalization=trainer.network.metadata.get('normalization'))
        for (_,e),values in zip(active,outputs):e.apply_outputs(values)
    scores=[sum(e.score for e in row)/len(row) for row in episodes]
    return scores,used,episodes


def freeze_unused(candidate,champion,width,neurons,used):
    # Restoring columns never observed in this rollout cannot change its outputs.
    for n in range(neurons):
        a=n*(width+1)+used;b=n*(width+1)+width
        candidate[a:b]=champion[a:b]


def measure(backend,trainer,mazes):
    scores,_,episodes=rollout(backend,trainer,[trainer.network.weights],mazes)
    row=episodes[0]
    return dict(mazes=len(row),escapes=sum(e.escaped for e in row),
                escape_rate=sum(e.escaped for e in row)/len(row),mean_score=scores[0],
                mean_unique_cells=sum(len(e.visits) for e in row)/len(row),
                mean_collisions=sum(e.collisions for e in row)/len(row))


def run(args):
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    if args.resume_model:
        trainer=Trainer.load(args.resume_model)
        if trainer.network.metadata.get('training_objective',{}).get('name')!='actual_exploration_v5':
            raise ValueError('Resume requires an actual_exploration_v5 model')
    else:
        fresh_action_model(args.settings_source,output/'initial.json',seed=args.seed)
        trainer=Trainer.load(output/'initial.json')
        trainer.config=replace(trainer.config,rules=replace(trainer.config.rules,
            until_failure=False,min_steps=0,max_steps=128,movement_reward=.1,exploration_reward=1.,
            revisit_penalty=.2,wall_penalty=5.,stationary_penalty=5.,penalize_stationary_immediately=True,
            progress_reward=0.,path_reward=0.,landmark_reward=0.,backtrack_penalty=0.,exit_reward=100.))
        trainer._metadata()
        trainer.network.metadata['training_objective']=dict(name='actual_exploration_v5',variant=5,
            method='evolution',route_action_match=False,random_initialization=True,
            input_freezing='restore never-observed input columns per candidate before selection')
    base_generation=trainer.network.generation
    trainer.network.save(output/'initial.json')
    data=maze_sets(args.dataset);groups={}
    for maze in data['train']:groups.setdefault((maze.width,maze.height),[]).append(maze)
    backend=MLXDenseBackend();rng=random.Random(args.seed)
    session=EvolutionSession(trainer.network.weights,population_size=4,elite_count=1,
                             mutation_sigma=.03,seed=args.seed,generation=base_generation)
    # Continue the map sampling stream at the saved generation.
    for _ in range(base_generation):
        for _,group in sorted(groups.items()):rng.choice(group)
    start=time.perf_counter()
    state=dict(status='running',variant=5,completed_rounds=0,rounds=args.rounds,seed=args.seed,
               source_generation=base_generation,target_generation=base_generation+args.rounds,
               resumed_from=str(args.resume_model) if args.resume_model else None,population=4,batch_mazes=len(groups),mutation_sigma=.03,
               initialization=trainer.network.metadata['initialization'],dataset=str(Path(args.dataset).resolve()))
    def save():
        state['elapsed_seconds']=time.perf_counter()-start
        p=output/'state.tmp';p.write_text(json.dumps(state,indent=2));p.replace(output/'state.json')
    try:
        state['before']=measure(backend,trainer,data['validation']);save()
        with (output/'rounds.jsonl').open('w') as log:
            for generation in range(base_generation+1,base_generation+args.rounds+1):
                mazes=[rng.choice(group) for _,group in sorted(groups.items())]
                candidates=session.ask()
                scores,used,episodes=rollout(backend,trainer,candidates,mazes)
                for candidate,count in zip(candidates,used):
                    freeze_unused(candidate,session.champion,*trainer.network.architecture[:2],count)
                winner=max(range(len(scores)),key=lambda i:scores[i])
                score,weights=session.tell(scores)
                trainer.network.weights=weights;trainer.network.generation=generation;trainer.network.score=score
                log.write(json.dumps(dict(generation=generation,fitness=scores,winner=winner,used_inputs=used,
                    mazes=[m.payload() for m in mazes],escapes=[sum(e.escaped for e in row) for row in episodes]))+'\n');log.flush()
                trainer.network.save(output/'latest.json')
                state.update(completed_rounds=generation-base_generation,generation=generation,last_score=score);save()
                if generation%10==0:print(json.dumps({k:state[k] for k in ('completed_rounds','last_score','elapsed_seconds')}),flush=True)
        state['after']=measure(backend,trainer,data['validation'])
        trainer.network.save(output/'final.json');state['status']='complete';save()
        print(json.dumps(state),flush=True)
    except Exception as error:
        state.update(status='error',error=str(error));save();raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--settings-source',type=Path)
    source.add_argument('--resume-model',type=Path)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--rounds',type=int,default=500)
    p.add_argument('--seed',type=int,default=2026102505)
    run(p.parse_args())
