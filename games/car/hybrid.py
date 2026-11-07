"""Five independent learners: safe driving rewards, last-50 credit, elite selection."""
import copy
import argparse
from collections import deque
import json
import math
from pathlib import Path
import random
import time

from ai.network import NeuralNetwork
from . import app
from .temporal import Adam, Experience, distribute_collision, forward_gradient

NATIVE_EVALUATION = False
SAFE_REWARD = .02
PROGRESS_REWARD = .05
COLLISION_PENALTY = 50.


def select_winner(evaluations, generation, generation_offset, *, trained_only=False, adaptation_generations=0):
    reference_only=trained_only or generation<=generation_offset+adaptation_generations
    return max(range(1 if reference_only else 0,len(evaluations)),key=lambda i:evaluations[i]['score'])


def driving_reward(delta, collided):
    # Safe time and signed road progress; circling/backwards motion is not progress.
    return (0. if collided else SAFE_REWARD) + PROGRESS_REWARD*delta


def features(car, cars, model=None):
    if model is not None and model.metadata.get('radar_mode','').startswith(('sectors','laser')):return app.model_observations(model,car,cars)
    readings = app.observations(car,cars)
    if app.RADAR_MODE in ('sectors15','sectors30','sectors30wide','sectors30echo','laser2'):return readings
    return [1-d/180 for d in readings[:7]] + readings[7:]


def wide_sector_view(network):
    if network.architecture[0]==90 and network.metadata.get('radar_mode')=='sectors30echo':return
    if network.architecture[0]!=60 or network.metadata.get('radar_mode') not in ('sectors30','sectors30wide','sectors30echo'):
        raise ValueError('Wide vision requires the existing 30-sector model')
    network.metadata.update(radar_mode='sectors30wide',observation_version='thirty_wide_sectors_distance_closing_v1')


def clone_network(source, rng=None, mutation=0.):
    clone = type(source)(source.architecture,seed=source.seed).set_backend('rust')
    clone.weights = [w+(rng.gauss(0,mutation) if mutation else 0.) for w in source.weights]
    clone.metadata = dict(source.metadata)
    clone.history = []
    clone.metadata.pop('validation',None)
    return clone


def add_throttle_output(source, seed):
    """Append one neuron; all existing weights and steering/brake outputs survive."""
    if source.architecture[-1] != 2:
        raise ValueError('Throttle expansion requires a two-output model')
    expanded = NeuralNetwork([*source.architecture[:-1],3],seed=source.seed).set_backend(source.backend)
    rng=random.Random(seed)
    expanded.weights=list(source.weights)+[rng.gauss(0,.1) for _ in range(source.architecture[-2]+1)]
    expanded.metadata=copy.deepcopy(source.metadata)
    expanded.metadata['action_version']='steering_brake_throttle50_v2'
    expanded.generation=source.generation
    expanded.history=copy.deepcopy(source.history)
    expanded.score=source.score
    return expanded


def add_radar_angles(source, seed):
    """Append eight inputs, randomizing only their first-layer connections."""
    if source.architecture[0] != 23:
        raise ValueError('Radar angle expansion requires 23 old inputs')
    expanded=source.expand_inputs(8)
    rng=random.Random(seed)
    for neuron in range(source.architecture[1]):
        start=neuron*32+23
        expanded.weights[start:start+8]=[rng.gauss(0,.1) for _ in range(8)]
    expanded.metadata=copy.deepcopy(source.metadata)
    expanded.metadata.update(radar_mode='cone4angles',observation_version='seven_rays_four_relative_angles_v7')
    expanded.generation=source.generation;expanded.score=source.score
    expanded.history=copy.deepcopy(source.history)
    return expanded


class Learner:
    def __init__(self, actor, seed):
        self.actor = actor
        self.rng = random.Random(seed)
        self.baseline = type(actor)([*actor.architecture[:-1],1],seed=seed).set_backend(actor.backend)
        self.baseline.weights = [self.rng.gauss(0,.1) for _ in self.baseline.weights]
        self.optimizer = Adam(actor.weight_count, rate=.0003)
        self.baseline_optimizer = Adam(self.baseline.weight_count, rate=.0003)
        self.attempts = 0
        self.sequence = 0
        self.begin()

    def begin(self, preserve_history=False):
        if not preserve_history:
            self.history = deque()
        self.gradient = [0.]*self.actor.weight_count
        self.baseline_gradient = [0.]*self.baseline.weight_count
        self.count = 0
        self.steps = 0
        self.reward = self.distance = 0.
        self.finished = False

    def finalize(self, entry):
        if entry.committed:
            if entry.reward == 0.:
                return  # Already learned its safe-driving reward; never replay it twice.
            outputs = [forward_gradient(self.actor,entry.inputs,i) for i in range(self.actor.architecture[-1])]
            latents = entry.latent if isinstance(entry.latent,tuple) else (entry.latent,)
            behavior = entry.behavior_mean if isinstance(entry.behavior_mean,tuple) else (entry.behavior_mean,)
            sigma = .15
            log_ratio = sum((z-old)**2-(z-mean)**2 for z,old,(mean,_) in zip(latents,behavior,outputs))/(2*sigma*sigma)
            ratio = math.exp(max(-20.,min(math.log(2.),log_ratio)))
            # Joint steering/braking likelihood, evaluated under current weights.
            for z,(mean,gradient) in zip(latents,outputs):
                for j,g in enumerate(gradient):
                    self.gradient[j] += entry.reward/50.*ratio*(z-mean)/sigma**2*g
            _,bg = forward_gradient(self.baseline,entry.inputs)
            for j,g in enumerate(bg):
                self.baseline_gradient[j] += entry.reward/50.*g
            self.count += 1
            self.reward += entry.reward
            entry.reward = 0.
            return
        advantage = entry.reward/50.-entry.baseline
        for j,g in enumerate(entry.policy_gradient):
            self.gradient[j] += advantage*g
        for j,g in enumerate(entry.baseline_gradient):
            self.baseline_gradient[j] += advantage*g
        self.count += 1
        self.reward += entry.reward
        entry.reward = 0.
        entry.committed = True

    def choose(self, tick, inputs):
        outputs = [forward_gradient(self.actor,inputs,i) for i in range(self.actor.architecture[-1])]
        sigma = .15
        means = tuple(mean for mean,_ in outputs)
        samples = tuple(self.rng.gauss(mean,sigma) for mean in means)
        action = app.decode_outputs([math.tanh(z) for z in samples])
        baseline,bg = forward_gradient(self.baseline,inputs)
        log_gradient = [sum((z-mean)/sigma**2*gradient[j] for z,(mean,gradient) in zip(samples,outputs))
                        for j in range(self.actor.weight_count)]
        if len(self.history)==50:
            self.finalize(self.history.popleft())
        self.history.append(Experience(self.sequence,inputs,action,None,log_gradient,baseline,bg,
                            latent=samples,behavior_mean=means))
        self.sequence += 1
        self.steps += 1
        return action

    def observe(self, delta, collided):
        self.history[-1].reward += driving_reward(delta,collided)
        self.distance += max(0.,delta)
        if collided:
            distribute_collision(self.history,penalty=COLLISION_PENALTY,mode='uniform50')

    def finish(self, collided):
        if self.finished:
            raise RuntimeError('Attempt was already finalized')
        for entry in self.history:
            self.finalize(entry)
        if collided:
            self.history.clear()
        n=max(1,self.count)
        self.optimizer.apply(self.actor.weights,[g/n for g in self.gradient])
        self.baseline_optimizer.apply(self.baseline.weights,[g/n for g in self.baseline_gradient])
        self.attempts += 1
        self.finished = True
        return dict(attempt=self.attempts,steps=self.steps,collision=collided,
                    reward=self.reward,distance=self.distance)


def train_round(learners,steps,offset,cars=None):
    """Keep survivors in place across weight updates; respawn only crashed cars."""
    if cars is None:
        cars=app.initial(offset)
    else:
        app.restart_crashed(cars,offset)
    for learner in learners:
        learner.begin(preserve_history=True)
    results=[None]*len(learners)
    for tick in range(steps):
        active=[not c['crashed'] for c in cars]
        if not any(active):
            break
        previous=[c['travel'] for c in cars]
        controls=[learner.choose(tick,features(c,cars)) if active[i] else 0.
                  for i,(learner,c) in enumerate(zip(learners,cars))]
        app.step(cars,[],controls=controls)
        for i,(learner,c) in enumerate(zip(learners,cars)):
            if not active[i]:
                continue
            learner.observe(c['travel']-previous[i],c['crashed'])
            if c['crashed']:
                results[i]=learner.finish(True)
    for i,learner in enumerate(learners):
        if results[i] is None:
            if learner.steps:
                results[i]=learner.finish(False)
            else:
                results[i]=dict(attempt=learner.attempts,steps=0,collision=False,waiting_for_spawn=True,reward=0.,distance=0.)
    return results


def evaluate_candidate(actor, traffic, steps, offset=0, initial_cars=None,overtake_reward=0.,background_models=(),pass_only=False,car_collision_penalty=50.):
    """Every candidate drives every starting slot/speed against frozen opponents."""
    if NATIVE_EVALUATION:
        from .native_evaluation import evaluate
        return evaluate(actor,traffic,steps,offset,initial_cars,overtake_reward,background_models,pass_only,car_collision_penalty)
    rows=[]
    for role in range(5):
        cars=app.initial(offset) if initial_cars is None else copy.deepcopy(initial_cars)
        reward=distance=0.
        progress_pending=0.
        from .overtaking import OvertakeTracker
        tracker=OvertakeTracker() if overtake_reward else None
        passes=0
        if tracker:tracker.update(cars)
        survived=0
        for tick in range(steps):
            # Evaluation still starts from standardized positions, with no respawns.
            controls=[]
            for i,c in enumerate(cars):
                network=background_models[i-5] if i>=5 else actor if i==role else traffic
                controls.append(app.decode_outputs(network.forward(features(c,cars,network)[:network.architecture[0]])) if not c['crashed'] else 0.)
            before=cars[role]['travel']
            events=[]
            if car_collision_penalty==50. and not app.DIRECTIONAL_COLLISIONS:app.step(cars,[],controls=controls)
            else:app.step(cars,[],controls=controls,events=events)
            delta=cars[role]['travel']-before
            collided=cars[role]['crashed']
            passed=tracker.update(cars)[role] if tracker else 0
            passes+=passed
            progress_pending+=delta
            if app.PROGRESS_ONLY_REWARD:
                if (tick+1)%10==0 or collided or tick+1==steps:
                    reward+=app.PROGRESS_ONLY_REWARD*max(0.,progress_pending);progress_pending=0.
            else:reward+=0. if pass_only else driving_reward(delta,collided)
            reward+=overtake_reward*passed
            distance+=max(0.,delta)
            survived=tick+1
            if collided:
                reward-=app.collision_cost(events,role,car_collision_penalty) if app.DIRECTIONAL_COLLISIONS else (car_collision_penalty if any(i==role and kind=='car' for i,kind,_ in events) else COLLISION_PENALTY)
                break
        rows.append(dict(role=role,reward=reward,distance=distance,steps=survived,
                         collision=cars[role]['crashed'],overtakes=passes))
    return dict(score=sum(r['reward'] for r in rows),collisions=sum(r['collision'] for r in rows),
                distance=sum(r['distance'] for r in rows),overtakes=sum(r['overtakes'] for r in rows),roles=rows)


def evaluate_suite(actor, traffic, steps, offsets, starts=None,overtake_reward=0.,background_models=(),pass_only=False,car_collision_penalty=50.):
    """Identical deterministic scenarios for each network; no training here."""
    runs=[dict(offset=offset, **evaluate_candidate(actor,traffic,steps,offset,initial_cars=None if starts is None else starts[i],overtake_reward=overtake_reward,background_models=background_models,pass_only=pass_only,car_collision_penalty=car_collision_penalty)) for i,offset in enumerate(offsets)]
    return dict(score=sum(r['score'] for r in runs),
                collisions=sum(r['collisions'] for r in runs),
                distance=sum(r['distance'] for r in runs),overtakes=sum(r.get('overtakes',0) for r in runs),
                test_rounds=len(offsets),attempts=len(offsets)*5,runs=runs)


def main():
    global NATIVE_EVALUATION
    parser=argparse.ArgumentParser(description=__doc__)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--initial-model',type=Path)
    source.add_argument('--fresh-laser2',action='store_true',help='Fresh two-height laser model with eight decision layers')
    source.add_argument('--fresh-sectors30',action='store_true',help='Fresh 30-sector front-focused local-vision model')
    source.add_argument('--fresh-sectors',action='store_true',help='New 15-sector local-vision model, signed speed output')
    source.add_argument('--fresh-brake',action='store_true',help='Fresh random 23-input, two-output steering/brake network')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cone-count',type=int,choices=range(34),help='Evenly spaced cones (0–33)')
    parser.add_argument('--no-cones',action='store_true',help='Train and evaluate without cones')
    parser.add_argument('--wide-sector-view',action='store_true',help='Keep 30-sector weights; switch to 220-degree coarse side vision')
    parser.add_argument('--radar-echo',action='store_true')
    parser.add_argument('--training-cars',type=int,choices=(5,10),default=5)
    parser.add_argument('--batch-size',type=int,choices=(0,50),default=0)
    parser.add_argument('--batch-backend',choices=('rust','mlx-gpu'),default='rust')
    parser.add_argument('--continue-survivors',action='store_true')
    parser.add_argument('--rust-evaluation',action='store_true',help='Whole evaluation rollout in Rust (pass-only sectors, no cones)')
    parser.add_argument('--steering-boost',type=float,default=0.)
    parser.add_argument('--max-brake',type=float,default=.5)
    parser.add_argument('--car-collision-penalty',type=float,default=50.,help='Penalty for car contact; wall/cone penalties stay 50')
    parser.add_argument('--background-speed-scale',type=float,default=1.,help='Multiplier for background cars only, in (0,1]')
    parser.add_argument('--background-model',type=Path,action='append',default=[],help='Frozen background model, one per additional car; up to 15')
    parser.add_argument('--progress-only-reward',type=float,default=0.,help='Per-unit positive road progress, spread uniformly over history; no survival reward')
    parser.add_argument('--directional-collisions',action='store_true',help='No penalty when clearly rear-ended; other contacts retain penalties')
    parser.add_argument('--pass-only',action='store_true',help='Only pass bonuses and collision penalties, no safe/progress rewards')
    parser.add_argument('--traffic-model',type=Path,help='Keep fixed evaluation opponents when continuing a run')
    parser.add_argument('--overtake-credit',choices=('latest','uniform50'),default='latest',help='Distribute pass bonus over the available 50-record history')
    parser.add_argument('--add-radar-angles',action='store_true',help='Append eight radar angle inputs with random new connections')
    parser.add_argument('--add-throttle',action='store_true',help='Preserve learned weights and append a random throttle output')
    parser.add_argument('--overtake-reward',type=float,default=0.,help='Bonus per confirmed safe pass')
    parser.add_argument('--hidden',type=int,nargs='+',help='Hidden layer widths for --fresh-brake; default: 8 8')
    parser.add_argument('--collision-credit',choices=('uniform50','latest20_linear','latest25_last10','split_distance20','split_distance20_recent3'),default='uniform50')
    parser.add_argument('--wall-credit',choices=('latest40_last25','uniform_last3','linear_distance20','split_distance20','split_distance20_recent3'),help='Wall-only collision credit schedule')
    parser.add_argument('--history-stride',type=int,default=1,help='Save one action per N steps; aggregate intervening rewards (rotating trainer)')
    parser.add_argument('--rotate',action='store_true',help='Asynchronous round-robin assignment across cars')
    parser.add_argument('--adaptation-generations',type=int,default=0,help='First N generations exclude parent from selection, then restore eligibility')
    parser.add_argument('--trained-only',action='store_true',help='Choose among trained candidates; keep parent as reference only')
    parser.add_argument('--generations',type=int,default=2)
    parser.add_argument('--random-scenarios',action='store_true',help='4–8 random cones, random starts and alternating convoy direction each generation')
    parser.add_argument('--balanced-sharing',action='store_true',help='Share networks across cars, balancing active drives with a ceil(cars/networks) cap')
    parser.add_argument('--learners',type=int,default=5,help='Number of independently trained networks in rotation')
    parser.add_argument('--rounds',type=int,default=100)
    parser.add_argument('--test-rounds',type=int,default=20)
    parser.add_argument('--steps',type=int,default=1000)
    parser.add_argument('--seed',type=int,default=20261105)
    parser.add_argument('--generation-offset',type=int,default=0)
    args=parser.parse_args()
    if not math.isfinite(args.steering_boost) or args.steering_boost<0:
        parser.error('--steering-boost must be nonnegative and finite')
    app.STEERING_BOOST=args.steering_boost
    if args.adaptation_generations<0 or (args.adaptation_generations and args.trained_only):
        parser.error('Adaptation count must be nonnegative and cannot combine with --trained-only')
    if (args.training_cars!=5 or args.batch_size or args.continue_survivors) and not (args.rotate and args.random_scenarios):
        parser.error('New batching/slots require rotation and random scenarios')
    if not math.isfinite(args.max_brake) or not 0<=args.max_brake<1:
        parser.error('--max-brake must be in [0,1)')
    app.MAX_BRAKE=args.max_brake
    NATIVE_EVALUATION=args.rust_evaluation
    if args.rust_evaluation and not (args.pass_only and args.no_cones):
        parser.error('--rust-evaluation requires --pass-only and --no-cones')
    if not math.isfinite(args.car_collision_penalty) or args.car_collision_penalty<0 or (args.car_collision_penalty!=50. and not args.rotate):
        parser.error('Nondefault car penalty must be nonnegative and requires rotation')
    if not math.isfinite(args.background_speed_scale) or not 0<args.background_speed_scale<=1:
        parser.error('--background-speed-scale must be in (0,1]')
    if len(args.background_model)>15 or (args.background_model and not (args.rotate and args.random_scenarios)):
        parser.error('Up to 15 background models require rotation and random scenarios')
    if args.pass_only and (not args.rotate or args.overtake_reward<=0):
        parser.error('--pass-only requires rotation and positive pass reward')
    if not math.isfinite(args.overtake_reward) or args.overtake_reward<0 or (args.overtake_reward and not args.rotate):
        parser.error('--overtake-reward must be nonnegative and requires --rotate')
    if args.wall_credit and not args.rotate:
        parser.error('--wall-credit requires --rotate')
    if args.collision_credit != 'uniform50' and not args.rotate:
        parser.error('--collision-credit requires --rotate')
    if args.history_stride < 1 or (args.history_stride != 1 and not args.rotate):
        parser.error('--history-stride must be positive; values above one require --rotate')
    if args.random_scenarios and (not args.rotate or args.cone_count is not None):
        parser.error('--random-scenarios requires --rotate and controls cone placement itself')
    if args.balanced_sharing and not args.rotate:parser.error('--balanced-sharing requires --rotate')
    if args.learners < 1 or (args.learners != 5 and not args.rotate):
        parser.error('--learners must be positive; values other than five require --rotate')
    if args.hidden is not None and (not args.fresh_brake or any(width<1 for width in args.hidden)):
        parser.error('--hidden requires --fresh-brake and positive layer widths')
    if args.generation_offset < 0:
        parser.error('Generation offset must be nonnegative')
    if min(args.generations,args.rounds,args.test_rounds,args.steps)<1:
        parser.error('Counts must be positive')
    if not math.isfinite(args.progress_only_reward) or args.progress_only_reward<0 or ((args.progress_only_reward or args.directional_collisions) and not args.rotate):
        parser.error("Progress/directional reward requires rotation and a finite nonnegative rate")
    app.PROGRESS_ONLY_REWARD=args.progress_only_reward;app.DIRECTIONAL_COLLISIONS=args.directional_collisions
    if args.output.exists():
        parser.error('Output must be a new directory')
    if args.fresh_laser2:
        from ai.laser_vision import LaserVisionNetwork
        parent=LaserVisionNetwork(seed=args.seed).set_backend('rust');parent.randomize()
        parent.metadata.update(game='car',track='training',traffic='convoy',radar_scale=3.,action_version='steering_signed_speed50_v1')
    elif args.fresh_sectors or args.fresh_sectors30:
        from ai.local_vision import LocalVisionNetwork, DEFAULT, FOCUSED
        parent=LocalVisionNetwork(FOCUSED if args.fresh_sectors30 else DEFAULT,seed=args.seed).set_backend('rust');parent.randomize()
        parent.metadata.update(game='car',track='training',traffic='convoy',radar_scale=3.,action_version='steering_signed_speed50_v1',observation_version='thirty_focused_sectors_distance_closing_v1' if args.fresh_sectors30 else 'fifteen_sectors_distance_closing_v1',radar_mode='sectors30' if args.fresh_sectors30 else 'sectors15')
    elif args.fresh_brake:
        parent=NeuralNetwork([23,*(args.hidden or [8,8]),2],seed=args.seed).set_backend('rust')
        initialization=random.Random(args.seed)
        parent.weights=[initialization.gauss(0,.35) for _ in parent.weights]
        parent.metadata.update(game='car',track='training',traffic='convoy',radar_scale=3.,action_version='steering_brake_0_to_50_v1')
    else:
        parent=NeuralNetwork.load(args.initial_model).set_backend('rust')
    if args.wide_sector_view:wide_sector_view(parent)
    if args.radar_echo:
        from ai.local_vision import add_echo_input
        parent=add_echo_input(parent)
    if args.add_radar_angles:parent=add_radar_angles(parent,args.seed+199)
    if args.add_throttle:parent=add_throttle_output(parent,args.seed+99)
    if parent.architecture[0] not in (11,23,30,31,60,90,366) or parent.architecture[-1] not in (1,2,3):
        parser.error('Expected 11, 23 or 31 input cone-radar model with one, two or three outputs')
    if not (args.fresh_brake or args.fresh_sectors or args.fresh_sectors30 or args.fresh_laser2) and parent.metadata.get('observation_version') not in ('seven_rays_four_relative_targets_v6','seven_rays_four_relative_angles_v7','fifteen_sectors_distance_closing_v1','thirty_focused_sectors_distance_closing_v1','thirty_wide_sectors_distance_closing_v1','thirty_wide_sectors_distance_closing_echo_v1','laser2_distance_closing_echo_v1'):
        parser.error('Relative-speed inputs differ from older checkpoints; use --fresh-brake for this experiment')
    source_generation=parent.generation
    if parent.architecture[0]==11:
        original=parent
        parent=original.expand_inputs(12).set_backend('rust')
        parent.metadata=dict(original.metadata)
        parent.generation=original.generation
        parent.score=original.score
    laser_inputs=parent.metadata.get('model_type')=='two_height_laser_local_v1'
    sector_inputs=parent.metadata.get('model_type')=='sector_local_vision_v1'
    angle_inputs=parent.architecture[0]==31
    if not (sector_inputs or laser_inputs):parent.metadata.update(radar_mode='cone4angles' if angle_inputs else 'cone4relative',observation_version='seven_rays_four_relative_angles_v7' if angle_inputs else 'seven_rays_four_relative_targets_v6')
    args.output.mkdir(parents=True)
    parent.save(args.output/'initial.json')
    app.configure_track('training',args.steps,cones=not args.no_cones,cone_count=args.cone_count);app.configure_traffic('convoy')
    app.configure_radar(3.);app.RADAR_MODE=parent.metadata['radar_mode'];app.TRACK.set_backend('rust')
    rng=random.Random(args.seed)
    test_rng=random.Random(args.seed+1)
    test_offsets=[test_rng.uniform(-12.,12.) for _ in range(args.test_rounds)]
    settings=dict(collision_recent_steps=3 if args.collision_credit=='split_distance20_recent3' else 0,collision_recent_share=1/3 if args.collision_credit=='split_distance20_recent3' else 0,wall_immediate_steps=3 if args.wall_credit=='split_distance20_recent3' else 0,wall_immediate_share=1/3 if args.wall_credit=='split_distance20_recent3' else 0,balanced_sharing=args.balanced_sharing,max_concurrent_drives_per_network=math.ceil(args.training_cars/args.learners) if args.balanced_sharing else None,progress_only_reward=args.progress_only_reward,collision_credit_zones='half_uniform_0_2_half_uniform_2_20_car_lengths' if args.collision_credit in ('split_distance20','split_distance20_recent3') else None,progress_credit='uniform_available_history' if args.progress_only_reward else 'current_record',progress_interval_steps=10,wall_recent_distance=4*app.CAR_RADIUS if args.wall_credit in ('split_distance20','split_distance20_recent3') else None,wall_recent_share=.5 if args.wall_credit in ('split_distance20','split_distance20_recent3') else None,wall_history_distance=40*app.CAR_RADIUS if args.wall_credit in ('linear_distance20','split_distance20','split_distance20_recent3') else None,directional_collisions=args.directional_collisions,rear_collision_penalty=0. if args.directional_collisions else args.car_collision_penalty,steering_boost=args.steering_boost,steering_curve='0.045*(u+boost*u^3)',adaptation_generations=args.adaptation_generations,parent_eligible_from=args.generation_offset+args.adaptation_generations+1 if not args.trained_only else None,batch_size=args.batch_size,batch_backend=args.batch_backend,continue_survivors=args.continue_survivors,evaluation_car_count=5+len(args.background_model),native_evaluation=args.rust_evaluation,random_scenarios=args.random_scenarios,engine='rust_gradients_radar_collisions_v1',traffic_model=str(args.traffic_model) if args.traffic_model else None,rotating_networks=args.rotate,trained_candidates_only=args.trained_only,architecture=list(parent.architecture),hidden_layers=list(parent.architecture[1:-1]),weight_count=parent.weight_count,radar_speed_reference='ego_longitudinal_and_radial_relative_velocity',fresh_initialization=args.fresh_brake or args.fresh_sectors or args.fresh_sectors30 or args.fresh_laser2,action_outputs=parent.architecture[-1],throttle_max_increase=.5 if parent.architecture[-1]==3 else 0.,overtake_reward=args.overtake_reward,overtake_credit=args.overtake_credit,brake_max_reduction=args.max_brake if parent.architecture[-1]>=2 else 0.,training_continuation='survivors_keep_pose_and_history_v2',delayed_credit='current_policy_gradient_with_importance_ratio_capped_at_2',radar_targets=4,network_inputs=parent.architecture[0],radar_angles=angle_inputs,radar_angle_degrees=math.degrees(2*app.CONE_HALF_ANGLE),cone_count=len(app.TRACK.cones),generation_offset=args.generation_offset,test_rounds=args.test_rounds,test_offsets=test_offsets,generations=args.generations,rounds=args.rounds,steps=args.steps,seed=args.seed,
                  learners=args.learners,training_attempts_per_generation=args.learners*args.rounds,history=512 if args.wall_credit in ('linear_distance20','split_distance20','split_distance20_recent3') else 50,history_stride=args.history_stride,history_reward='sum_between_samples',history_boundary='new_sample_on_new_session',credit=args.collision_credit,wall_credit=args.wall_credit,safe_reward=SAFE_REWARD,
                  progress_reward=PROGRESS_REWARD,collision_penalty=COLLISION_PENALTY,car_collision_penalty=args.car_collision_penalty,
                  exploration_sigma=.15,learning_rate=.0003,mutation_sigma=.03,
                  initial_generation=source_generation,protected_parent=not args.trained_only and not args.adaptation_generations,
                  selection='20 test scenarios by default, each in all five slots/speeds against fixed initial-model opponents; no learning or exploration',
                  holdout='Offsets -8 and +8, reported only, not used for selection')
    if sector_inputs:
        settings.update(model_type='sector_local_vision_v1',radar_mode=app.RADAR_MODE,radar_targets=None,radar_sectors=parent.sectors,radar_angle_degrees=220 if app.RADAR_MODE in ('sectors30wide','sectors30echo') else 180,sector_width_degrees=12 if app.RADAR_MODE=='sectors15' else None,observation_version=parent.metadata['observation_version'],local_layers=3,local_channels=parent.metadata.get('sector_channels',[2,4,4,4]),decision_hidden=[32,24,16,8,4],action_version='steering_signed_speed50_v1',throttle_max_increase=.5)
    if sector_inputs:
        from .sector_radar import sector_edges
        settings['sector_edges_radians']=sector_edges(app.RADAR_MODE)
        settings['front_to_side_density']=None if app.RADAR_MODE in ('sectors30wide','sectors30echo') else 2 if app.RADAR_MODE=='sectors30' else 1
    if laser_inputs:
        from .laser_radar import ray_angles
        settings.update(model_type=parent.metadata['model_type'],radar_mode='laser2',radar_targets=None,radar_sectors=None,radar_angle_degrees=220,ray_angles=ray_angles(),rays_per_height=61,sensor_heights=[.5,3.],curb_height=2.,car_body_height=[1.,5.],local_layers=3,local_channels=[3,4,4,4],decision_hidden=list(parent.architecture[4:-1]),action_version='steering_signed_speed50_v1',observation_version=parent.metadata['observation_version'],throttle_max_increase=.5)
    if args.random_scenarios:
        settings.update(cone_count=None,cone_count_range=[4,8],starts='random_each_attempt',direction='alternates_each_generation',training_continuation='new_random_pose_each_attempt',selection='Parent and children reevaluated on identical new starts and layout each generation',holdout='Two additional random starts on the current layout; not used for selection')
    (args.output/'settings.json').write_text(json.dumps(settings,indent=2))
    traffic=clone_network(NeuralNetwork.load(args.traffic_model) if args.traffic_model else parent)
    if args.wide_sector_view:wide_sector_view(traffic)
    if parent.architecture[0]==90:
        from ai.local_vision import add_echo_input
        traffic=add_echo_input(traffic)
    if not laser_inputs and (((traffic.architecture[1:-1] != parent.architecture[1:-1] or traffic.architecture[0] not in (23,parent.architecture[0])) or traffic.architecture[-1] not in (2,parent.architecture[-1])) or traffic.metadata.get("observation_version") not in ("seven_rays_four_relative_targets_v6",parent.metadata.get("observation_version"))):
        parser.error("Traffic model must share hidden architecture and observations; legacy two-output traffic is allowed")
    if laser_inputs and traffic.metadata.get('radar_mode') not in ('sectors30wide','sectors30echo'):
        parser.error('Laser experiment requires a frozen old 30-wide-sector traffic model')
    traffic.save(args.output/"traffic-reference.json")
    background=[];background_paths=[]
    for i,path in enumerate(args.background_model):
        net=NeuralNetwork.load(path).set_backend('rust')
        if args.wide_sector_view:wide_sector_view(net)
        if parent.architecture[0]==90:net=add_echo_input(net)
        if not laser_inputs and (net.architecture!=parent.architecture or net.metadata.get('observation_version')!=parent.metadata.get('observation_version')):
            parser.error('Background models must match actor architecture and observations')
        if laser_inputs and net.metadata.get('radar_mode') not in ('sectors30wide','sectors30echo'):
            parser.error('Laser background requires old 30-wide-sector observations')
        dest=args.output/f'background-{i}.json';net.save(dest)
        background.append(net);background_paths.append(str(dest.resolve()))
    settings.update(car_count=args.training_cars+len(background),training_cars=args.training_cars,background_models=background_paths,background_speed_scale=args.background_speed_scale,
                    reward_mode='progress_passes_directional_collisions' if args.progress_only_reward else 'passes_and_collisions' if args.pass_only else 'safe_progress_passes_collisions',
                    safe_reward=0. if args.pass_only else SAFE_REWARD,
                    progress_reward=args.progress_only_reward or (0. if args.pass_only else PROGRESS_REWARD))
    if args.no_cones:settings.update(cone_count=0,cone_count_range=[0,0])
    (args.output/'settings.json').write_text(json.dumps(settings,indent=2))
    scenario=None
    test_starts=holdout_starts=None
    def prepare_scenario(gen):
        nonlocal scenario,test_starts,holdout_starts
        if not args.random_scenarios:return
        from .scenarios import Scenario
        scenario=Scenario(args.seed,gen,car_count=5+len(background),no_cones=args.no_cones,background_speed_scale=args.background_speed_scale)
        test_starts=scenario.evaluation_starts(args.test_rounds)
        holdout_starts=scenario.evaluation_starts(2,holdout=True)
        # Evaluation remains five roles + fixed background traffic, as before.
        if args.training_cars!=5:
            scenario=Scenario(args.seed,gen,car_count=args.training_cars+len(background),no_cones=args.no_cones,background_speed_scale=args.background_speed_scale,training_count=args.training_cars)
    def evaluate_current(n):
        return evaluate_suite(n,traffic,args.steps,test_offsets,starts=test_starts,overtake_reward=args.overtake_reward,background_models=background,pass_only=args.pass_only,car_collision_penalty=args.car_collision_penalty)
    def holdout_current(n):
        return [evaluate_candidate(n,traffic,args.steps,o,initial_cars=None if holdout_starts is None else holdout_starts[i],overtake_reward=args.overtake_reward,background_models=background,pass_only=args.pass_only,car_collision_penalty=args.car_collision_penalty) for i,o in enumerate((-8,8))]
    prepare_scenario(args.generation_offset+1)
    started=time.monotonic()
    with (args.output/'metrics.jsonl').open('w') as log:
        initial=evaluate_current(parent)
        initial_holdout=holdout_current(parent)
        log.write(json.dumps(dict(generation=0,evaluation=initial,holdout=initial_holdout))+'\n');log.flush()
        training_cars=app.initial(0)
        learners=[]
        car_histories=[deque() for _ in training_cars]
        for gen in range(args.generation_offset+1,args.generation_offset+args.generations+1):
            if args.random_scenarios:
                prepare_scenario(gen)
                training_cars=scenario.initial()
                car_histories=[deque() for _ in training_cars]
                layout=dict(**scenario.payload(),test_starts=test_starts,holdout_starts=holdout_starts,training_starts=copy.deepcopy(training_cars))
                (args.output/f'generation-{gen}-scenario.json').write_text(json.dumps(layout,indent=2))
                log.write(json.dumps(dict(generation=gen,scenario=layout))+'\n');log.flush()
            previous_learners=learners
            learners=[Learner(clone_network(parent,rng,0. if i==0 else .03),rng.randrange(2**32)) for i in range(args.learners)]
            for current,previous in zip(learners,previous_learners):
                current.history=deque(previous.history)
                current.sequence=previous.sequence
            if args.rotate:
                from .rotating import train_generation
                def report_attempt(row):
                    log.write(json.dumps(dict(generation=gen,training_attempt=row))+'\n');log.flush()
                rotation=train_generation([l.actor for l in learners],args.steps,args.rounds,
                                          training_cars,car_histories,args.seed+gen*100,on_attempt=report_attempt,history_stride=args.history_stride,credit_mode=args.collision_credit,scenario=scenario,wall_credit_mode=args.wall_credit,overtake_reward=args.overtake_reward,overtake_credit=args.overtake_credit,background_models=background,pass_only=args.pass_only,car_collision_penalty=args.car_collision_penalty,batch_size=args.batch_size,batch_backend=args.batch_backend,continue_survivors=args.continue_survivors,balanced_sharing=args.balanced_sharing)
                log.write(json.dumps(dict(generation=gen,rotation_summary={k:v for k,v in rotation.items() if k!='records'}))+'\n');log.flush()
            else:
                for round_index in range(args.rounds):
                    stats=train_round(learners,args.steps,0,cars=training_cars)
                    log.write(json.dumps(dict(generation=gen,round=round_index+1,learners=stats))+'\n');log.flush()
            # Evaluate incumbent as reference; eligibility is controlled by --trained-only.
            candidates=[parent]+[l.actor for l in learners]
            evaluations=[]
            for candidate_index,n in enumerate(candidates):
                result=evaluate_current(n)
                evaluations.append(result)
                log.write(json.dumps(dict(generation=gen,test_candidate=candidate_index,evaluation=result))+'\n');log.flush()
            winner=select_winner(evaluations,gen,args.generation_offset,trained_only=args.trained_only,adaptation_generations=args.adaptation_generations)
            parent=clone_network(candidates[winner])
            parent.generation=gen;parent.score=evaluations[winner]['score']
            if scenario is not None:parent.metadata['scenario']=scenario.payload()
            parent.metadata.update(training_method='hybrid_uniform50_v1',experiment=settings)
            parent.save(args.output/f'generation-{gen}.json');parent.save(args.output/'model.json')
            for i,learner in enumerate(learners):
                learner.actor.generation=gen
                learner.actor.score=evaluations[i+1]['score']
                learner.actor.metadata.update(training_method='hybrid_uniform50_v1',experiment=settings)
                learner.actor.save(args.output/f'generation-{gen}-learner-{i}.json')
            row=dict(generation=gen,parent_eligible=not args.trained_only and gen>args.generation_offset+args.adaptation_generations,winner='parent' if winner==0 else f'learner-{winner-1}',
                     evaluations=evaluations,holdout=holdout_current(parent),
                     elapsed_seconds=time.monotonic()-started)
            log.write(json.dumps(row)+'\n');log.flush();print(json.dumps(row),flush=True)
    (args.output/'complete.json').write_text(json.dumps(dict(generations=args.generations,last_generation=args.generation_offset+args.generations,elapsed_seconds=time.monotonic()-started)))


if __name__=='__main__':
    main()
