"""Variant 6: separate encoders and randomized starts on successful routes."""
import argparse
import copy
import json
import random
import time
from pathlib import Path
from ai.branched import BranchedNetwork, MLXBranchedBackend, MODEL_TYPE, BRANCHES
from ai_service.generic import EvolutionSession
from games.maze.training import Trainer
from games.maze.world import Maze
from scripts.train_exploration import maze_sets,measure,rollout


def route_groups(dataset,split='train'):
    groups={}
    with (Path(dataset)/'successful-routes.jsonl').open() as stream:
        for line in stream:
            route=json.loads(line)
            if route['split']==split:
                m=route['maze'];groups.setdefault((m['width'],m['height']),[]).append(route)
    return groups


def sample_starts(groups,rng):
    mazes=[]
    for _,routes in sorted(groups.items()):
        route=rng.choice(routes);m=route['maze']
        # Samples are pre-action poses on a completed route, never its terminal exit.
        pose=rng.choice(route['samples'])['pose']
        mazes.append(Maze(m['name'],tuple(m['rows']),(pose['x'],pose['y']),pose['heading']))
    return mazes


def run(args):
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    trainer=Trainer.load(args.settings_source)
    model=BranchedNetwork(seed=args.seed);model.randomize()
    model.metadata.update(copy.deepcopy(trainer.network.metadata))
    model.metadata.pop('normalization',None);model.metadata.pop('history_hidden_widths',None)
    model.metadata.update(model_type=MODEL_TYPE,branches=[list(b) for b in BRANCHES],
        initialization=dict(method='independent Gaussian per layer',seed=args.seed,transferred_weights=False),
        training_objective=dict(name='random_route_starts_branched_v6',variant=6,method='evolution',
            random_initialization=True,route_action_match=False,empty_history_at_start=True,
            starts='uniform route then uniform pre-action pose, one route per size',
            memory='previous attempted relative actions; unchanged from v5'))
    trainer.network=model
    from dataclasses import replace
    trainer.config=replace(trainer.config,seed=args.seed)
    trainer._metadata();model.save(output/'initial.json')
    groups=route_groups(args.dataset);data=maze_sets(args.dataset)
    backend=MLXBranchedBackend();rng=random.Random(args.seed)
    # Fixed random validation starts are drawn only from held-out routes.
    validation_groups=route_groups(args.dataset,'validation')
    validation_rng=random.Random(args.seed+1)
    validation_starts=[m for _ in range(30) for m in sample_starts(validation_groups,validation_rng)]
    session=EvolutionSession(model.weights,population_size=4,elite_count=1,mutation_sigma=.03,seed=args.seed)
    start=time.perf_counter()
    state=dict(status='running',variant=6,source_generation=0,target_generation=args.rounds,
               completed_rounds=0,seed=args.seed,branches=[list(b) for b in BRANCHES],
               weights=model.weight_count,reward_rules=model.metadata['config']['rules'])
    def save():
        state['elapsed_seconds']=time.perf_counter()-start
        p=output/'state.tmp';p.write_text(json.dumps(state,indent=2));p.replace(output/'state.json')
    try:
        state['before']=measure(backend,trainer,data['validation'])
        state['random_starts_before']=measure(backend,trainer,validation_starts);save()
        with (output/'rounds.jsonl').open('w') as log:
            for generation in range(1,args.rounds+1):
                mazes=sample_starts(groups,rng);candidates=session.ask()
                scores,used,episodes=rollout(backend,trainer,candidates,mazes)
                for c,u in zip(candidates,used):model.freeze_unused(c,session.champion,u)
                score,model.weights=session.tell(scores);model.score=score;model.generation=generation
                log.write(json.dumps(dict(generation=generation,fitness=scores,used_inputs=used,
                    mazes=[m.payload() for m in mazes]))+'\n');log.flush()
                model.save(output/'latest.json')
                state.update(completed_rounds=generation,last_score=score);save()
                if generation%50==0:print(json.dumps(dict(generation=generation,score=score)),flush=True)
        state['after']=measure(backend,trainer,data['validation'])
        state['random_starts_after']=measure(backend,trainer,validation_starts)
        model.save(output/'final.json');state['status']='complete';save();print(json.dumps(state),flush=True)
    except Exception as e:
        state.update(status='error',error=str(e));save();raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--settings-source',type=Path,required=True)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=2026102507)
    p.add_argument('--rounds',type=int,default=1000)
    run(p.parse_args())
