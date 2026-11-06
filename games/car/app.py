"""V2: identical agents, opposite directions, seven obstacle sensors."""
import argparse
import json
import math
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ai.network import NeuralNetwork

RADIUS, HALF_WIDTH, CAR_RADIUS = 140., 38., 7.
PERIMETER = 560 + 2 * math.pi * RADIUS
ANGLES = tuple(math.radians(a) for a in (-90, -60, -30, 0, 30, 60, 90))
GENERATIONS = 100
INPUTS, HIDDEN = 9, 8
RADAR_RANGE = 180.
RADAR_RADIUS = 90.
RADAR_OFFSET = 90.
RADAR_HALF_ANGLE = math.pi / 3
CONE_HALF_ANGLE = math.pi / 3
NATIVE_CAR_KERNELS = True
ARCHITECTURE = [INPUTS, HIDDEN, HIDDEN, 1]
network = NeuralNetwork(ARCHITECTURE)
WEIGHT_COUNT = network.weight_count
COLLISION_PENALTY = 50.
MAX_BRAKE = .5
MODEL = Path(__file__).parent / 'models' / 'model_radar_9_8_8_1.json'


from .track import Track, DEFAULT_TRACK

TRACK = DEFAULT_TRACK
clearance, progress = TRACK.clearance, TRACK.progress
PERIMETER, PATH = TRACK.perimeter, TRACK.path
SIMULATION_STEPS = 650
TRAFFIC = 'opposite'
REPLAY_SCENARIO = None
REPLAY_BACKGROUND = []
RADAR_MODE = 'legacy'
RADAR_SCALE = 1.
SPEED_FACTORS = (.8, .9, 1., 1.1, 1.2)


def configure_track(name='s_curve', steps=None, *, cones=True, cone_count=None):
    global TRACK, clearance, progress, PERIMETER, PATH, HALF_WIDTH, SIMULATION_STEPS, cars
    TRACK = Track.generate(name)
    if cone_count is not None:
        if type(cone_count) is not int or not 0 <= cone_count <= 33:
            raise ValueError('Cone count must be between 0 and 33')
        TRACK.cones.clear()
        for i in range(cone_count):
            pose = TRACK.pose(TRACK.perimeter*(i+.5)/cone_count, -12. if i%2==0 else 12.)
            TRACK.cones.append(dict(x=pose['x'],y=pose['y'],z=pose['z'],radius=6.,kind='cone',crashed=False))
    if not cones:
        TRACK.cones.clear()
    clearance, progress = TRACK.clearance, TRACK.progress
    PERIMETER, PATH, HALF_WIDTH = TRACK.perimeter, TRACK.path, TRACK.half_width
    SIMULATION_STEPS = steps or (max(650, math.ceil(PERIMETER / 3 * 1.5)) if name in ('figure_eight', 'training') else 650)
    cars = initial()
    status.update(track=name, simulation_steps=SIMULATION_STEPS)


def configure_radar(scale=3.):
    global RADAR_RANGE, RADAR_RADIUS, RADAR_OFFSET, RADAR_SCALE
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Radar scale must be positive and finite')
    RADAR_SCALE = scale
    RADAR_RANGE, RADAR_RADIUS, RADAR_OFFSET = 180*scale, 90*scale, 90*scale
    status['radar_scale'] = scale


def configure_traffic(mode):
    global TRAFFIC, cars
    if mode not in ('opposite', 'convoy'):
        raise ValueError('Unknown traffic mode')
    TRAFFIC = mode
    cars = initial()
    status.update(traffic=mode)


def others(car, traffic):
    return [c for c in ([traffic] if isinstance(traffic, dict) else traffic) if c is not car]


def same_level(a, b):
    if abs(a.get('z', 0.) - b.get('z', 0.)) < 2*CAR_RADIUS:
        return True
    # Road-following sensors must still see traffic ahead on a ramp. The
    # two crossing decks are far apart along the road, unlike ramp neighbours.
    first = progress(a['x'], a['y'], a.get('z', 0.))
    second = progress(b['x'], b['y'], b.get('z', 0.))
    delta = abs(first-second)
    return min(delta, PERIMETER-delta) <= RADAR_RANGE * 1.5


def sensors(car, other):
    obstacles = [c for c in others(car, other)+TRACK.cones if not c.get('crashed', False)
                 and math.hypot(c['x']-car['x'], c['y']-car['y']) <= 180+c.get('radius', CAR_RADIUS)
                 and same_level(car, c)]
    if TRACK.native is not None:
        return TRACK.native.sensors(car['x'], car['y'], car.get('z', 0.), car['heading'],
                                    ANGLES, [(c['x'], c['y'], c.get('radius', CAR_RADIUS)) for c in obstacles])
    readings = []
    for angle in ANGLES:
        dx, dy = math.cos(car['heading'] + angle), math.sin(car['heading'] + angle)
        distance = 0.
        for _ in range(55):
            gap = clearance(car['x'] + distance * dx, car['y'] + distance * dy, car.get('z', 0.))
            if gap < .15 or distance >= 180:
                break
            distance = min(180, distance + max(.1, gap * .95))
        # Every ray reports the nearest car body or wall.
        for obstacle in obstacles:
            ox, oy = obstacle['x'] - car['x'], obstacle['y'] - car['y']
            projection = ox * dx + oy * dy
            discriminant = obstacle.get('radius', CAR_RADIUS) ** 2 - (ox * ox + oy * oy - projection ** 2)
            if discriminant >= 0:
                near = projection - math.sqrt(discriminant)
                far = projection + math.sqrt(discriminant)
                if far >= 0:
                    distance = min(distance, max(0., near))
        readings.append(distance)
    return readings


def radar_angles(car, other):
    """Signed bearing and relative velocity direction in ego coordinates, radians."""
    ch,sh=math.cos(car['heading']),math.sin(car['heading'])
    dx,dy=other['x']-car['x'],other['y']-car['y']
    bearing=math.atan2(-dx*sh+dy*ch,dx*ch+dy*sh)
    speed=0. if other.get('kind')=='cone' else other.get('speed',3*other.get('speed_factor',1.))
    ego=car.get('speed',3*car.get('speed_factor',1.))
    vx=speed*math.cos(other.get('heading',0.))-ego*ch
    vy=speed*math.sin(other.get('heading',0.))-ego*sh
    forward,lateral=vx*ch+vy*sh,-vx*sh+vy*ch
    # Direction is undefined at zero relative speed: use zero.
    motion=math.atan2(lateral,forward) if math.hypot(forward,lateral)>1e-8 else 0.
    return bearing,motion


def radar(car, other):
    if RADAR_MODE in ('sectors15','sectors30','sectors30wide'):
        import sys
        from .sector_radar import scan
        sectors=scan(sys.modules[__name__],car,other)
        nearest=min(sectors,key=lambda r:r['distance'])
        return dict(nearest,shape='sectors',sectors=sectors,range=RADAR_RANGE,targets=[],half_angle=math.radians(110) if RADAR_MODE=='sectors30wide' else math.pi/2,center_x=car['x'],center_y=car['y'],radius=RADAR_RANGE)
    objects = others(car, other)+TRACK.cones
    if NATIVE_CAR_KERNELS and TRACK.native is not None and RADAR_MODE in ('cone', 'cone4', 'cone4relative', 'cone4angles'):
        from ai.rust_backend import native_module
        rows = native_module().cone_targets(
            (car['x'], car['y'], car['heading'], car.get('speed', 3*car.get('speed_factor', 1.)), car['crashed']),
            [(c['x'], c['y'], c.get('heading', 0.),
              0. if c.get('kind') == 'cone' else c.get('speed', 3*c.get('speed_factor', 1.)),
              c.get('radius', CAR_RADIUS), c.get('crashed', False)) for c in objects],
            RADAR_RANGE, CONE_HALF_ANGLE)
        detections = []
        for index, gap, forward, lateral, speed, closing, relative in rows:
            c = objects[index]
            # Preserve Python hypot rounding and stable ordering of equal-distance targets.
            gap = max(0., math.hypot(c['x']-car['x'], c['y']-car['y'])-c.get('radius', CAR_RADIUS))
            if not same_level(car, c):
                continue
            detections.append(dict(target_id=c.get('target_id'), detected=True, shape='cone',
                half_angle=CONE_HALF_ANGLE, distance=gap, forward=forward, lateral=lateral,
                speed=speed, closing_speed=closing, relative_speed=relative, kind=c.get('kind', 'car'),
                proximity=max(0., 1-gap/RADAR_RANGE), bearing=0., range=RADAR_RANGE,
                radius=RADAR_RADIUS, offset=0., center_x=car['x'], center_y=car['y']))
    else:
        detections = [_radar_one(car, c) for c in objects]
    if RADAR_MODE == 'cone4angles':
        # Native and Python kernels preserve object order among their detections.
        visible_objects=[objects[row[0]] for row in rows if same_level(car,objects[row[0]])] if NATIVE_CAR_KERNELS and TRACK.native is not None else objects
        for detection,obj in zip(detections,visible_objects):
            detection['bearing_angle'],detection['motion_angle']=radar_angles(car,obj)
    visible = [r for r in detections if r['detected']]
    if visible:
        nearest = min(visible, key=lambda r: r['distance']).copy()
        nearest['targets'] = [dict(distance=r['distance'], forward=r['forward'], lateral=r['lateral'], kind=r['kind'], speed=r.get('speed'), closing_speed=r.get('closing_speed'), relative_speed=r.get('relative_speed'), proximity=r['proximity'], target_id=r.get('target_id'),bearing_angle=r.get('bearing_angle',0.),motion_angle=r.get('motion_angle',0.)) for r in sorted(visible,key=lambda r:r['distance'])]
        if RADAR_MODE in ('cone4', 'cone4relative', 'cone4angles'):
            nearest['targets'] = nearest['targets'][:4]
        return nearest
    # Keep exactly two radar inputs, even for an empty traffic list.
    return dict(_radar_one(car, dict(car, crashed=True)), targets=[])


def radar_line_of_sight(car, target):
    """March towards the target's near surface; road edges block radar.

    Interpolate elevation so ramp neighbours remain visible. same_level()
    separately rejects traffic on the other deck of an overpass.
    """
    dx, dy = target['x']-car['x'], target['y']-car['y']
    length = math.hypot(dx, dy)
    end = max(0., length-target.get('radius', CAR_RADIUS))
    distance = 0.
    while distance < end:
        fraction = distance / length
        z = car.get('z', 0.) + fraction*(target.get('z', 0.)-car.get('z', 0.))
        gap = clearance(car['x']+fraction*dx, car['y']+fraction*dy, z)
        if gap < .15:
            return False
        distance += max(.1, min(8., gap*.9))
    return True


def _cone_radar_one(car, other):
    dx, dy = other['x']-car['x'], other['y']-car['y']
    distance = math.hypot(dx, dy)
    forward = dx*math.cos(car['heading']) + dy*math.sin(car['heading'])
    lateral = -dx*math.sin(car['heading']) + dy*math.cos(car['heading'])
    # Centre-in-sector convention: 120 degrees total, no wall ray marching.
    detected = (not car['crashed'] and not other.get('crashed', False)
                and distance < RADAR_RANGE and forward >= 0
                and abs(math.atan2(lateral, forward)) <= CONE_HALF_ANGLE
                and same_level(car, other))
    speed = 0. if other.get('kind') == 'cone' else other.get('speed', 3*other.get('speed_factor', 1.))
    ego_speed = car.get('speed', 3*car.get('speed_factor', 1.))
    vx = speed*math.cos(other.get('heading', 0.))-ego_speed*math.cos(car['heading'])
    vy = speed*math.sin(other.get('heading', 0.))-ego_speed*math.sin(car['heading'])
    # Positive means the range is shrinking; units are world units per step.
    closing_speed = -(vx*dx+vy*dy)/distance if distance else 0.
    relative_speed = vx*math.cos(car['heading']) + vy*math.sin(car['heading'])
    gap = max(0., distance-other.get('radius', CAR_RADIUS))
    return dict(target_id=other.get('target_id') if detected else None, detected=detected, shape='cone', half_angle=CONE_HALF_ANGLE,
                distance=gap if detected else None, forward=forward if detected else None,
                lateral=lateral if detected else None, speed=speed if detected else None,
                closing_speed=closing_speed if detected else None,
                relative_speed=relative_speed if detected else None,
                kind=other.get('kind', 'car') if detected else None,
                proximity=max(0., 1-gap/RADAR_RANGE) if detected else 0.,
                bearing=0., range=RADAR_RANGE, radius=RADAR_RADIUS, offset=0.,
                center_x=car['x'], center_y=car['y'])


def _radar_one(car, other):
    if RADAR_MODE in ('cone', 'cone4', 'cone4relative', 'cone4angles'):
        return _cone_radar_one(car, other)
    dx, dy = other['x']-car['x'], other['y']-car['y']
    distance = math.hypot(dx, dy)
    angle = (math.atan2(dy, dx)-car['heading']+math.pi) % (2*math.pi)-math.pi
    # Circle in front of the car: detect overlap with the other car body.
    center_x = car['x'] + RADAR_OFFSET*math.cos(car['heading'])
    center_y = car['y'] + RADAR_OFFSET*math.sin(car['heading'])
    target_radius = other.get('radius', CAR_RADIUS)
    gap = max(0., distance-target_radius)
    detected = (not car['crashed'] and not other['crashed'] and gap < RADAR_RANGE and same_level(car, other)
                and math.hypot(other['x']-center_x, other['y']-center_y) <= RADAR_RADIUS + target_radius
                and radar_line_of_sight(car, other))
    proximity = max(0., 1-gap/RADAR_RANGE) if detected else 0.
    bearing = max(-1., min(1., angle/RADAR_HALF_ANGLE))*proximity
    return dict(detected=detected, distance=gap if detected else None,
                forward=(dx*math.cos(car['heading'])+dy*math.sin(car['heading'])) if detected else None,
                lateral=(-dx*math.sin(car['heading'])+dy*math.cos(car['heading'])) if detected else None,
                kind=other.get('kind', 'car') if detected else None,
                proximity=proximity, bearing=bearing, range=RADAR_RANGE, radius=RADAR_RADIUS, offset=RADAR_OFFSET, center_x=center_x, center_y=center_y)


def observations(car, other):
    if RADAR_MODE in ('sectors15','sectors30','sectors30wide'):
        import sys
        from .sector_radar import inputs
        return inputs(sys.modules[__name__],car,other)
    detection = radar(car, other)
    if RADAR_MODE in ('cone4', 'cone4relative', 'cone4angles'):
        values = []
        for target in detection['targets'][:4]:
            values.extend([target['proximity'], target['lateral']/RADAR_RANGE,
                           (max(-1., min(1., target['relative_speed']/7.2)) if RADAR_MODE in ('cone4relative','cone4angles') else target['speed']/3.6), max(-1., min(1., target['closing_speed']/7.2))])
        values.extend([0.]*(16-len(values)))
        if RADAR_MODE == 'cone4angles':
            angles=[]
            for target in detection['targets'][:4]:
                angles.extend([target['bearing_angle']/math.pi,target['motion_angle']/math.pi])
            values.extend(angles+[0.]*(8-len(angles)))
        return sensors(car, other) + values
    if RADAR_MODE == 'cone':
        values = ([detection['proximity'], detection['lateral']/RADAR_RANGE,
                   detection['speed']/3.6, max(-1., min(1., detection['closing_speed']/7.2))]
                  if detection['detected'] else [0., 0., 0., 0.])
        return sensors(car, other) + values
    lateral = max(-1.,min(1.,detection['lateral']/RADAR_RADIUS)) if detection['detected'] else 0.
    return sensors(car, other) + [detection['proximity'], lateral if RADAR_MODE == 'spatial' else detection['bearing']]


def migrate_sensor_weights(weights):
    old = NeuralNetwork([7, 8, 8, 1])
    old._check_weights(weights)
    old.weights = list(weights)
    return old.expand_inputs(2).weights


def policy(weights, readings):
    # Observation normalization belongs to this game, not the reusable network.
    values = readings if RADAR_MODE in ('sectors15','sectors30','sectors30wide') else [1 - distance / 180 for distance in readings[:7]] + readings[7:]
    return decode_outputs(network.forward(values, weights))


def decode_outputs(outputs):
    """Legacy models steer only; braking strength is configurable through MAX_BRAKE."""
    if len(outputs) == 1:
        return outputs[0]
    if len(outputs) == 2 and RADAR_MODE in ('sectors15','sectors30','sectors30wide'):
        return outputs[0],max(0.,-outputs[1]),max(0.,outputs[1])
    if len(outputs) == 2:
        return outputs[0], (outputs[1]+1.)/2.
    if len(outputs) == 3:
        return outputs[0], (outputs[1]+1.)/2., max(0.,outputs[2])
    raise ValueError('Expected steering, optional brake and throttle outputs')


def initial(offset=0):
    if TRAFFIC == 'convoy':
        start = TRACK.perimeter * .12
        return [dict(TRACK.pose(start-TRACK.perimeter*i/len(SPEED_FACTORS), offset), direction=1, speed_factor=factor,
                     travel=0., crashed=False, restarts=0)
                for i,factor in enumerate(SPEED_FACTORS)]
    if TRACK.name != 's_curve':
        # Start away from the crossing, side by side in opposite directions.
        along = TRACK.perimeter * .12 if TRACK.name == 'figure_eight' else 140.
        result = []
        for direction, lateral in ((1, -18-offset), (-1, 18-offset)):
            pose = TRACK.pose(along, lateral)
            pose['heading'] += math.pi if direction == -1 else 0.
            result.append(dict(pose, direction=direction, travel=0., crashed=False, restarts=0))
        return result
    return [dict(x=400., y=428. + offset, heading=math.pi, direction=1, travel=0., crashed=False, restarts=0),
            dict(x=400., y=392. + offset, heading=0., direction=-1, travel=0., crashed=False, restarts=0)]


def swept_distance(old, cars):
    # Continuous relative motion in xyz; old 2D callers retain z=0.
    positions = [(c['x'], c['y'], c.get('z', 0.)) for c in cars]
    previous = [tuple(p) + (0.,)*(3-len(p)) for p in old]
    relative = [previous[0][i]-previous[1][i] for i in range(3)]
    velocity = [positions[0][i]-positions[1][i]-relative[i] for i in range(3)]
    square = sum(v*v for v in velocity)
    t = max(0., min(1., -sum(r*v for r,v in zip(relative,velocity))/square)) if square else 0.
    return math.sqrt(sum((r+t*v)**2 for r,v in zip(relative,velocity)))


def restart_crashed(cars, offset=0):
    starts = initial(offset)
    for i, car in enumerate(cars):
        if not car['crashed']:
            continue
        start = starts[i]
        if any(math.dist((start['x'],start['y'],start.get('z',0.)),(c['x'],c['y'],c['z'])) < CAR_RADIUS+c['radius']+2 for c in TRACK.cones):
            continue
        # Every active car must clear the spawn point.
        if any(not c['crashed'] and math.dist((start['x'],start['y'],start.get('z',0.)),
               (c['x'],c['y'],c.get('z',0.))) < 2*CAR_RADIUS+6 for c in cars if c is not car):
            continue
        start['restarts'] = car['restarts'] + 1
        car.clear()
        car.update(start)


def step(cars, weights, *, controls=None, events=None):
    # All decisions use the same pre-movement state.
    if controls is None:
        controls = [policy(weights, observations(c, cars)) if not c['crashed'] else 0. for c in cars]
    controls = [(v,0.,0.) if isinstance(v,(float,int)) else tuple(v)+(0.,) if len(v)==2 else tuple(v) for v in controls]
    if len(controls) != len(cars) or any(len(v)!=3 or not all(math.isfinite(x) for x in v) or not -1<=v[0]<=1 or not all(0<=a<=1 for a in v[1:]) for v in controls):
        raise ValueError('Each car needs steering in [-1,1] and brake/throttle in [0,1]')
    active = [not c['crashed'] for c in cars]
    old = [(c['x'], c['y'], c.get('z', 0.)) for c in cars]
    reward = 0.
    reason = ''
    for idx, (c, (steer, brake, throttle)) in enumerate(zip(cars, controls)):
        if c['crashed']:
            continue
        before = progress(c['x'], c['y'], c.get('z', 0.))
        c['heading'] += steer * .045
        speed = 3 * c.get('speed_factor', 1.) * (1.-MAX_BRAKE*brake)*(1.+.5*throttle)
        c.update(brake=brake,throttle=throttle,speed=speed)
        c['x'] += speed * math.cos(c['heading'])
        c['y'] += speed * math.sin(c['heading'])
        c['z'] = TRACK.locate(c['x'], c['y'], c.get('z', 0.))[2]
        delta = ((progress(c['x'], c['y'], c['z']) - before + PERIMETER / 2) % PERIMETER - PERIMETER / 2) * c['direction']
        c['travel'] += delta
        gap = clearance(c['x'], c['y'], c['z']) - CAR_RADIUS
        reward -= .4 * max(0., (12 - gap) / 12) ** 2
        # Check the movement segment as well as its endpoint.
        if min(clearance(old[idx][0] + (c['x']-old[idx][0])*t,
                         old[idx][1] + (c['y']-old[idx][1])*t,
                         old[idx][2] + (c['z']-old[idx][2])*t) for t in (0,.5,1)) <= CAR_RADIUS:
            c['crashed'] = True
            reason = 'Veggkontakt'
            if events is not None:
                events.append((idx, 'wall', None))
    native_gaps = None
    if NATIVE_CAR_KERNELS and TRACK.native is not None:
        from ai.rust_backend import native_module
        native_gaps = native_module().separations(old,
            [(c['x'], c['y'], c.get('z', 0.)) for c in cars],
            [(c['x'], c['y'], c['z'], c['radius']) for c in TRACK.cones], CAR_RADIUS)
    for i, car in enumerate(cars):
        if not active[i]:
            continue
        for cone_index, cone in enumerate(TRACK.cones):
            separation = native_gaps[0][i][cone_index] if native_gaps is not None else swept_distance([old[i],(cone['x'],cone['y'],cone['z'])], [car,cone])-CAR_RADIUS-cone['radius']
            reward -= .4*max(0.,(12-separation)/12)**2
            if separation <= 0:
                car['crashed'] = True
                reason = 'Kjeglekontakt'
                if events is not None:
                    events.append((i, 'cone', cone.get('target_id')))
    for i in range(len(cars)):
        for j in range(i+1, len(cars)):
            if not (active[i] and active[j]):
                continue
            separation = native_gaps[1][i][j] if native_gaps is not None else swept_distance([old[i],old[j]], [cars[i],cars[j]]) - 2*CAR_RADIUS
            reward -= 2 * max(0., (20 - separation) / 20) ** 2
            if separation <= 0:
                reason = 'Bilene kolliderte'
                cars[i]['crashed'] = cars[j]['crashed'] = True
                if events is not None:
                    events.extend([(i, 'car', cars[j].get('target_id')), (j, 'car', cars[i].get('target_id'))])
    if reason:
        reward -= COLLISION_PENALTY
    return reward, reason


def evaluate(weights, offset=0, live=False):
    global cars, reason
    attempt = initial(offset)
    score = 0.
    outcome = ''
    last_event, event_ticks = '', 0
    frames = []
    with lock:
        label = dict(display_generation=status['generation'], display_candidate=status['candidate'])
    for tick in range(SIMULATION_STEPS):
        restart_crashed(attempt, offset)
        reward, outcome = step(attempt, weights)
        score += reward
        if outcome:
            last_event, event_ticks = outcome, 20
        if tick == SIMULATION_STEPS - 1:
            outcome = f'{SIMULATION_STEPS} steg fullført · omstarter: ' + ' / '.join(str(c['restarts'] + int(c['crashed'])) for c in attempt)
        if live:
            frames.append(([c.copy() for c in attempt],
                           outcome or (last_event if event_ticks > 0 else ''), tick + 1, round(score, 1)))
        event_ticks -= 1
    if live:
        # Keep the newest complete attempt; never make training wait for playback.
        try:
            recordings.get_nowait()
        except queue.Empty:
            pass
        recordings.put_nowait((label, frames))
    return score, min(c['travel'] for c in attempt) / PERIMETER, outcome


lock = threading.Lock()
recordings = queue.Queue(maxsize=1)
best = [0.] * WEIGHT_COUNT
status = dict(generation=0, generations=GENERATIONS, best_score=None, training=True,
              architecture=ARCHITECTURE, candidate=0, population=36, step=0, current_score=0, speed=1, phase='training')
cars = initial()
reason = ''


def train(additional=GENERATIONS, fast=False, training_speed=0):
    global best, network
    resume = fast and MODEL.exists()
    if resume:
        network = NeuralNetwork.load(MODEL, expected_architecture=ARCHITECTURE).set_backend(network.backend)
        best = network.weights[:]
    start = network.generation if resume else 0
    network.metadata.update(game='car', collision_penalty=COLLISION_PENALTY,
                            objective='obstacle_penalties_only', simulation_steps=SIMULATION_STEPS,
                            track=TRACK.name, traffic=TRAFFIC, radar_mode=RADAR_MODE, radar_scale=RADAR_SCALE, speed_factors=list(SPEED_FACTORS) if TRAFFIC == 'convoy' else [1.,1.], radar_occlusion='none' if RADAR_MODE in ('cone', 'cone4', 'cone4relative', 'cone4angles') else 'road_edges_v1', observation_version='seven_rays_four_relative_angles_v7' if RADAR_MODE == 'cone4angles' else 'seven_rays_four_relative_targets_v6' if RADAR_MODE == 'cone4relative' else 'seven_rays_four_cone_targets_v5' if RADAR_MODE == 'cone4' else 'seven_rays_cone_motion_v4' if RADAR_MODE == 'cone' else 'seven_rays_spatial_radar_occluded_v3' if RADAR_MODE == 'spatial' else 'seven_rays_circular_radar_v1')
    network.metadata.pop('validation', None)
    with lock:
        status.update(fast=True, speed=training_speed or 1, generations=start + additional)

    def candidate(generation, index):
        with lock:
            status.update(generation=generation, candidate=index, phase='training')

    def result(trained):
        global best
        with lock:
            best = trained.weights[:]
            status['best_score'] = round(trained.score, 1)

    network.train(lambda weights: evaluate(weights, live=True)[0], additional,
                  resume=resume, mutation_sigma=lambda gen: .12 if gen < 40 else .05,
                  checkpoint=MODEL, on_candidate=candidate, on_result=result)
    with lock:
        status['phase'] = 'validation'
    validation = [evaluate(best, offset, live=True) for offset in (-8, 0, 8)]
    network.metadata['validation'] = validation
    network.save(MODEL)
    with lock:
        status.update(training=False, validation=validation, phase='replay', fast=False, speed=1)
    animate()


def animate():
    evaluate(best, live=True)


def replay_live():
    """Run saved weights directly, without waiting for a full recorded lap."""
    global cars, reason
    while True:
        attempt, score = (REPLAY_SCENARIO.initial() if REPLAY_SCENARIO else initial()), 0.
        for tick in range(SIMULATION_STEPS):
            started = time.monotonic()
            if REPLAY_SCENARIO:REPLAY_SCENARIO.restart_crashed(attempt)
            else:restart_crashed(attempt)
            controls=None
            if REPLAY_BACKGROUND:
                controls=[]
                for i,c in enumerate(attempt):
                    count=REPLAY_SCENARIO.training_count if REPLAY_SCENARIO else 5
                    net=network if i<count else REPLAY_BACKGROUND[i-count]
                    controls.append(0. if c['crashed'] else decode_outputs(net.forward(observations(c,attempt))))
            reward, event = step(attempt, best,controls=controls)
            score += reward
            with lock:
                cars = [c.copy() for c in attempt]
                reason = event
                status.update(step=tick+1, current_score=round(score, 1))
                speed = status['speed']
            time.sleep(max(0., 1/(30*speed) - (time.monotonic()-started)))


def display_recordings():
    global cars, reason
    recording = None
    while True:
        try:
            recording = recordings.get(timeout=.1) if recording is None else recordings.get_nowait()
        except queue.Empty:
            if recording is None:
                continue
        label, frames = recording
        for positions, event, tick, score in frames:
            with lock:
                cars = [c.copy() for c in positions]
                reason = event
                status.update(label, step=tick, current_score=score)
                speed = status['speed']
            time.sleep(1 / (30 * speed))
        time.sleep(.5)


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/speed':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length < 100:
                raise ValueError()
            speed = json.loads(self.rfile.read(length))['speed']
            if speed not in (1, 3, 10, 30):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            self.send_error(400)
            return
        with lock:
            status['speed'] = speed

        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/track':
            data, kind = json.dumps(TRACK.payload()).encode(), 'application/json'
        elif self.path == '/api/state':
            with lock:
                payload = dict(status, reason=reason, angles=ANGLES,
                    cars=[dict(c, sensors=[] if RADAR_MODE in ('sectors15','sectors30','sectors30wide') else sensors(c, cars), radar=radar(c, cars),
                               pitch=TRACK.pitch(c['x'], c['y'], c.get('z', 0.), c['heading']),
                               lap=round(100*max(0,c['travel'])/PERIMETER,1)) for i,c in enumerate(cars)])
            data, kind = json.dumps(payload).encode(), 'application/json'
        elif self.path.startswith('/renderer/'):
            name = self.path.removeprefix('/renderer/')
            kinds = {'.js': 'text/javascript', '.wasm': 'application/wasm', '.html': 'text/html; charset=utf-8'}
            asset = Path(__file__).with_name('renderer') / name
            if Path(name).name != name or asset.suffix not in kinds or not asset.is_file():
                self.send_error(404)
                return
            data, kind = asset.read_bytes(), kinds[asset.suffix]
        elif self.path == '/':
            data, kind = Path(__file__).with_name('demo.html').read_bytes(), 'text/html; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


def main():
    global network, best, ARCHITECTURE, WEIGHT_COUNT, MODEL, RADAR_MODE, REPLAY_SCENARIO, REPLAY_BACKGROUND, MAX_BRAKE
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-brake', type=float, default=None, help='Maximum fraction of base speed removed by full braking')
    parser.add_argument('--radar-scale', type=float, default=3., help='Radar radius and range multiplier')
    parser.add_argument('--radar-mode', choices=('legacy', 'spatial', 'cone', 'cone4', 'cone4relative', 'cone4angles', 'sectors15', 'sectors30', 'sectors30wide'), help='spatial: independent distance and lateral position; requires matching training')
    parser.add_argument('--traffic', choices=('convoy', 'opposite'), default='convoy')
    parser.add_argument('--cone-count',type=int,choices=range(34),help='Evenly spaced cones (0–33)')
    parser.add_argument('--no-cones',action='store_true',help='Remove cones from sensors, physics and rendering')
    parser.add_argument('--track', choices=Track.NAMES, default='s_curve')
    parser.add_argument('--steps', type=int, help='Simulation steps per attempt')
    parser.add_argument('--backend', choices=('python', 'rust'), default='python')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--replay', action='store_true', help='Show saved model instead of live training')
    parser.add_argument('--fast-generations', type=int, default=0)
    parser.add_argument('--training-speed', type=int, choices=(0, 1, 3, 10, 30), default=0)
    parser.add_argument('--hidden', type=int, nargs='*', default=[8, 8], help='Hidden layer sizes; empty means no hidden layers')
    parser.add_argument('--model', type=Path, help='Separate checkpoint path for an experiment')
    parser.add_argument('--seed', type=int, help='Random seed for a new experiment')
    args = parser.parse_args()
    if args.max_brake is not None and (not math.isfinite(args.max_brake) or not 0 <= args.max_brake < 1):
        parser.error('--max-brake must be in [0, 1)')
    MAX_BRAKE = args.max_brake if args.max_brake is not None else .5
    if args.steps is not None and args.steps < 1:
        parser.error('--steps must be positive')
    if not math.isfinite(args.radar_scale) or args.radar_scale <= 0:
        parser.error('--radar-scale must be positive and finite')
    configure_radar(args.radar_scale)
    configure_track(args.track, args.steps, cones=not args.no_cones,cone_count=args.cone_count)
    configure_traffic(args.traffic)
    try:
        RADAR_MODE = args.radar_mode or ('cone4' if args.track == 'training' and not args.replay else 'legacy')
        ARCHITECTURE = [60 if RADAR_MODE in ('sectors30','sectors30wide') else 30 if RADAR_MODE == 'sectors15' else 31 if RADAR_MODE == 'cone4angles' else 23 if RADAR_MODE in ('cone4', 'cone4relative', 'cone4angles') else 11 if RADAR_MODE == 'cone' else INPUTS, *args.hidden, 1]
        network = NeuralNetwork(ARCHITECTURE, seed=args.seed)
        WEIGHT_COUNT = network.weight_count
        best = network.weights[:]
        prefix = 'model_radar_' if args.replay or (args.track == 's_curve' and args.traffic == 'opposite') else f'model_{args.track}_{args.traffic}_'
        MODEL = args.model or Path(__file__).parent / 'models' / (prefix + '_'.join(map(str, ARCHITECTURE)) + '.json')
        status['architecture'] = ARCHITECTURE
        resuming = args.replay or bool(args.fast_generations and MODEL.exists())
        if resuming:
            network = NeuralNetwork.load(MODEL)
            if args.max_brake is None:
                MAX_BRAKE = network.metadata.get('experiment', {}).get('brake_max_reduction', .5)
            ARCHITECTURE = list(network.architecture)
            WEIGHT_COUNT = network.weight_count
            status['architecture'] = ARCHITECTURE
        saved_mode = network.metadata.get('radar_mode', 'legacy')
        RADAR_MODE = args.radar_mode or (saved_mode if resuming else ('cone4' if args.track == 'training' else 'legacy'))
        if resuming and RADAR_MODE != saved_mode:
            raise ValueError('Radar input differs from saved weights; use matching radar mode or train a new model')
        if network.architecture[0] != (60 if RADAR_MODE in ('sectors30','sectors30wide') else 30 if RADAR_MODE == 'sectors15' else 31 if RADAR_MODE == 'cone4angles' else 23 if RADAR_MODE in ('cone4', 'cone4relative', 'cone4angles') else 11 if RADAR_MODE == 'cone' else 9):
            raise ValueError('Network input count does not match radar mode')
        status['radar_mode'] = RADAR_MODE
        network.set_backend(args.backend)
        TRACK.set_backend(args.backend)
        status['backend'] = args.backend
        if args.replay and network.metadata.get('scenario'):
            import sys
            from .scenarios import Scenario
            saved = network.metadata['scenario']
            REPLAY_SCENARIO = Scenario(saved['seed'], saved['generation'],world=sys.modules[__name__],car_count=saved.get('car_count',5),no_cones=not saved['cones'],background_speed_scale=saved.get('background_speed_scale',1.),training_count=saved.get('training_count',5))
            REPLAY_SCENARIO.cones = saved['cones']
            REPLAY_SCENARIO.direction = saved['direction']
            TRACK.cones = REPLAY_SCENARIO.cones
            paths=network.metadata.get('experiment',{}).get('background_models',[])
            REPLAY_BACKGROUND=[NeuralNetwork.load(p).set_backend(args.backend) for p in paths]
            if len(REPLAY_BACKGROUND)!=saved.get('car_count',5)-saved.get('training_count',5):raise ValueError('Missing fixed background models')
            status['background_cars']=len(REPLAY_BACKGROUND)
            status['training_cars']=saved.get('training_count',5)
            status['scenario_direction'] = saved['direction_label']
    except (ValueError, KeyError, OSError, TypeError, RuntimeError) as error:
        parser.error(str(error))
    if args.fast_generations < 0:
        parser.error('--fast-generations must be positive')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    if MODEL.exists() and args.replay:
        best = network.weights[:]
        status.update(generation=network.generation, generations=max(network.generation, network.metadata.get('experiment', {}).get('generation_offset', 0) + network.metadata.get('experiment', {}).get('generations', GENERATIONS)),
                      best_score=round(network.score, 1) if network.score is not None else None,
                      training=False, phase='replay', validation=network.metadata.get('validation', []) if network.metadata.get('track') == TRACK.name and network.metadata.get('traffic', 'opposite') == TRAFFIC else [])
        threading.Thread(target=replay_live, daemon=True).start()
    else:
        threading.Thread(target=display_recordings, daemon=True).start()
        threading.Thread(target=train, args=(args.fast_generations or GENERATIONS, bool(args.fast_generations), args.training_speed), daemon=True).start()
    print(f'AI-spill · Bilspill: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()
