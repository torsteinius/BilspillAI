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
ARCHITECTURE = [INPUTS, HIDDEN, HIDDEN, 1]
network = NeuralNetwork(ARCHITECTURE)
WEIGHT_COUNT = network.weight_count
COLLISION_PENALTY = 50.
MODEL = Path(__file__).parent / 'models' / 'model_radar_9_8_8_1.json'


from .track import clearance, progress, PERIMETER, PATH


def sensors(car, other):
    readings = []
    for angle in ANGLES:
        dx, dy = math.cos(car['heading'] + angle), math.sin(car['heading'] + angle)
        distance = 0.
        for _ in range(55):
            gap = clearance(car['x'] + distance * dx, car['y'] + distance * dy)
            if gap < .15 or distance >= 180:
                break
            distance = min(180, distance + max(.1, gap * .95))
        # Exact ray/circle intersection with the other car.
        ox, oy = other['x'] - car['x'], other['y'] - car['y']
        projection = ox * dx + oy * dy
        discriminant = CAR_RADIUS ** 2 - (ox * ox + oy * oy - projection ** 2)
        if not other.get('crashed', False) and discriminant >= 0:
            near = projection - math.sqrt(discriminant)
            far = projection + math.sqrt(discriminant)
            if far >= 0:
                distance = min(distance, max(0., near))
        readings.append(distance)
    return readings


def radar(car, other):
    dx, dy = other['x']-car['x'], other['y']-car['y']
    distance = math.hypot(dx, dy)
    angle = (math.atan2(dy, dx)-car['heading']+math.pi) % (2*math.pi)-math.pi
    # Circle in front of the car: detect overlap with the other car body.
    center_x = car['x'] + RADAR_OFFSET*math.cos(car['heading'])
    center_y = car['y'] + RADAR_OFFSET*math.sin(car['heading'])
    gap = max(0., distance-CAR_RADIUS)
    detected = (not car['crashed'] and not other['crashed'] and gap < RADAR_RANGE
                and math.hypot(other['x']-center_x, other['y']-center_y) <= RADAR_RADIUS + CAR_RADIUS)
    proximity = max(0., 1-gap/RADAR_RANGE) if detected else 0.
    bearing = max(-1., min(1., angle/RADAR_HALF_ANGLE))*proximity
    return dict(detected=detected, distance=gap if detected else None,
                proximity=proximity, bearing=bearing, range=RADAR_RANGE, radius=RADAR_RADIUS, offset=RADAR_OFFSET, center_x=center_x, center_y=center_y)


def observations(car, other):
    detection = radar(car, other)
    return sensors(car, other) + [detection['proximity'], detection['bearing']]


def migrate_sensor_weights(weights):
    old = NeuralNetwork([7, 8, 8, 1])
    old._check_weights(weights)
    old.weights = list(weights)
    return old.expand_inputs(2).weights


def policy(weights, readings):
    # Observation normalization belongs to this game, not the reusable network.
    values = [1 - distance / 180 for distance in readings[:7]] + readings[7:]
    return network.forward(values, weights)[0]


def initial(offset=0):
    return [dict(x=400., y=428. + offset, heading=math.pi, direction=1, travel=0., crashed=False, restarts=0),
            dict(x=400., y=392. + offset, heading=0., direction=-1, travel=0., crashed=False, restarts=0)]


def swept_distance(old, cars):
    rx, ry = old[0][0] - old[1][0], old[0][1] - old[1][1]
    vx = cars[0]['x'] - cars[1]['x'] - rx
    vy = cars[0]['y'] - cars[1]['y'] - ry
    t = max(0., min(1., -(rx * vx + ry * vy) / (vx * vx + vy * vy))) if vx * vx + vy * vy else 0.
    return math.hypot(rx + t * vx, ry + t * vy)


def restart_crashed(cars, offset=0):
    starts = initial(offset)
    for i, car in enumerate(cars):
        if not car['crashed']:
            continue
        start, other = starts[i], cars[1-i]
        # Wait off track if the surviving car is passing the spawn point.
        if not other['crashed'] and math.hypot(start['x']-other['x'], start['y']-other['y']) < 2*CAR_RADIUS + 6:
            continue
        start['restarts'] = car['restarts'] + 1
        car.clear()
        car.update(start)


def step(cars, weights):
    # Both decisions use the same pre-movement state.
    controls = [policy(weights, observations(cars[i], cars[1-i])) if not cars[i]['crashed'] else 0. for i in range(2)]
    active = [not c['crashed'] for c in cars]
    old = [(c['x'], c['y']) for c in cars]
    reward = 0.
    reason = ''
    for c, steer in zip(cars, controls):
        if c['crashed']:
            continue
        before = progress(c['x'], c['y'])
        c['heading'] += steer * .045
        c['x'] += 3 * math.cos(c['heading'])
        c['y'] += 3 * math.sin(c['heading'])
        delta = ((progress(c['x'], c['y']) - before + PERIMETER / 2) % PERIMETER - PERIMETER / 2) * c['direction']
        c['travel'] += delta
        gap = clearance(c['x'], c['y']) - CAR_RADIUS
        reward -= .4 * max(0., (12 - gap) / 12) ** 2
        # Check the movement segment as well as its endpoint.
        idx = 0 if c is cars[0] else 1
        if min(clearance(old[idx][0] + (c['x']-old[idx][0])*t,
                         old[idx][1] + (c['y']-old[idx][1])*t) for t in (0,.5,1)) <= CAR_RADIUS:
            c['crashed'] = True
            reason = 'Veggkontakt'
    separation = swept_distance(old, cars) - 2 * CAR_RADIUS
    if all(active):
        reward -= 2 * max(0., (20 - separation) / 20) ** 2
    if all(active) and separation <= 0:
        reason = 'Bilene kolliderte'
        for c in cars:
            c['crashed'] = True
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
    for tick in range(650):
        restart_crashed(attempt, offset)
        reward, outcome = step(attempt, weights)
        score += reward
        if outcome:
            last_event, event_ticks = outcome, 20
        if tick == 649:
            outcome = '650 steg fullført · omstarter: ' + ' / '.join(str(c['restarts'] + int(c['crashed'])) for c in attempt)
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
        network = NeuralNetwork.load(MODEL, expected_architecture=ARCHITECTURE)
        best = network.weights[:]
    start = network.generation if resume else 0
    network.metadata.update(game='car', collision_penalty=COLLISION_PENALTY,
                            objective='obstacle_penalties_only', simulation_steps=650,
                            track='s_curve', observation_version='seven_rays_circular_radar_v1')
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
            data, kind = json.dumps(dict(path=PATH, width=2*HALF_WIDTH)).encode(), 'application/json'
        elif self.path == '/api/state':
            with lock:
                payload = dict(status, reason=reason, angles=ANGLES,
                    cars=[dict(c, sensors=sensors(c, cars[1-i]), radar=radar(c, cars[1-i]), lap=round(100*max(0,c['travel'])/PERIMETER,1)) for i,c in enumerate(cars)])
            data, kind = json.dumps(payload).encode(), 'application/json'
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
    global network, best, ARCHITECTURE, WEIGHT_COUNT, MODEL
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--replay', action='store_true', help='Show saved model instead of live training')
    parser.add_argument('--fast-generations', type=int, default=0)
    parser.add_argument('--training-speed', type=int, choices=(0, 1, 3, 10, 30), default=0)
    parser.add_argument('--hidden', type=int, nargs='*', default=[8, 8], help='Hidden layer sizes; empty means no hidden layers')
    parser.add_argument('--model', type=Path, help='Separate checkpoint path for an experiment')
    parser.add_argument('--seed', type=int, help='Random seed for a new experiment')
    args = parser.parse_args()
    try:
        ARCHITECTURE = [INPUTS, *args.hidden, 1]
        network = NeuralNetwork(ARCHITECTURE, seed=args.seed)
        WEIGHT_COUNT = network.weight_count
        best = network.weights[:]
        MODEL = args.model or Path(__file__).parent / 'models' / ('model_radar_' + '_'.join(map(str, ARCHITECTURE)) + '.json')
        status['architecture'] = ARCHITECTURE
        if args.replay or (args.fast_generations and MODEL.exists()):
            network = NeuralNetwork.load(MODEL, expected_architecture=ARCHITECTURE)
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.error(str(error))
    if args.fast_generations < 0:
        parser.error('--fast-generations must be positive')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    threading.Thread(target=display_recordings, daemon=True).start()
    if MODEL.exists() and args.replay:
        best = network.weights[:]
        status.update(generation=network.generation, generations=max(GENERATIONS, network.generation),
                      best_score=round(network.score, 1) if network.score is not None else None,
                      training=False, phase='replay', validation=network.metadata.get('validation', []))
        threading.Thread(target=animate, daemon=True).start()
    else:
        threading.Thread(target=train, args=(args.fast_generations or GENERATIONS, bool(args.fast_generations), args.training_speed), daemon=True).start()
    print(f'AI-spill · Bilspill: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()
