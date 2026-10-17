"""Dependency-free Python driving demo. Run: python3 demo.py."""
import argparse
import json
import math
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Stadium centreline: two straights joined by radius-140 semicircles.
RADIUS, HALF_WIDTH, CAR_RADIUS = 140.0, 38.0, 7.0
ANGLES = (-math.pi / 2, -math.pi / 4, math.pi / 4, math.pi / 2)
PERIMETER = 560 + 2 * math.pi * RADIUS


def clearance(x, y):
    nearest_x = max(260, min(540, x))
    return HALF_WIDTH - abs(math.hypot(x - nearest_x, y - 270) - RADIUS)


def sensors(x, y, heading):
    result = []
    for angle in ANGLES:
        dx, dy = math.cos(heading + angle), math.sin(heading + angle)
        distance = 0.0
        for _ in range(70):
            gap = clearance(x + distance * dx, y + distance * dy)
            if gap < .1 or distance >= 180:
                break
            distance = min(180, distance + max(.1, gap * .9))
        result.append(distance)
    return result


def policy(weights, readings):
    inputs = [v / 180 for v in readings] + [1]
    hidden = [math.tanh(sum(weights[j * 5 + k] * inputs[k] for k in range(5))) for j in range(5)]
    return math.tanh(sum(weights[25 + j] * hidden[j] for j in range(5)) + weights[30])


def progress(x, y):
    if x < 260:
        angle = math.atan2(y - 270, x - 260)
        if angle < 0:
            angle += 2 * math.pi
        return 560 + math.pi * RADIUS + (angle - math.pi / 2) * RADIUS
    if x > 540:
        return 280 + (math.atan2(y - 270, x - 540) + math.pi / 2) * RADIUS
    return x - 260 if y < 270 else 280 + math.pi * RADIUS + 540 - x


def initial():
    return {'x': 260., 'y': 130., 'heading': 0., 'travel': 0., 'steps': 0, 'crashed': False, 'score': 0.}


def step(car, weights):
    readings = sensors(car['x'], car['y'], car['heading'])
    steer = policy(weights, readings)
    before = progress(car['x'], car['y'])
    car['heading'] += steer * .045
    car['x'] += 3 * math.cos(car['heading'])
    car['y'] += 3 * math.sin(car['heading'])
    delta = (progress(car['x'], car['y']) - before + PERIMETER / 2) % PERIMETER - PERIMETER / 2
    car['travel'] += delta
    car['steps'] += 1
    gap = clearance(car['x'], car['y']) - CAR_RADIUS
    car['crashed'] = gap <= 0
    car['score'] += delta - .5 * max(0, (18 - gap) / 18) ** 2
    if car['crashed']:
        car['score'] -= 100
    return car['crashed'] or car['travel'] >= PERIMETER or car['steps'] >= 650


def evaluate(weights):
    car = initial()
    while not step(car, weights):
        pass
    return car['score']


lock = threading.Lock()
best = [0.] * 31
status = {'generation': 0, 'score': -100., 'training': True}
car = initial()


def train():
    global best
    rng = random.Random(14)
    population = [[rng.gauss(0, .7) for _ in range(31)] for _ in range(32)]
    champion, champion_score = population[0], -float('inf')
    for generation in range(1, 61):
        ranked = sorted(((evaluate(w), w) for w in population), key=lambda item: item[0], reverse=True)
        if ranked[0][0] > champion_score:
            champion_score, champion = ranked[0]
        with lock:
            best = champion[:]
            status.update(generation=generation, score=round(champion_score), training=True)
        elites = [w for _, w in ranked[:6]]
        spread = .3 if generation < 25 else .13
        population = [w[:] for w in elites]
        while len(population) < 32:
            parent = rng.choice(elites)
            population.append([v + rng.gauss(0, spread) for v in parent])
    with lock:
        status['training'] = False


def animate():
    global car
    current = best[:]
    while True:
        with lock:
            done = step(car, current)
        time.sleep(1 / 30)
        if done:
            time.sleep(.6)
            with lock:
                car = initial()
                current = best[:]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/state':
            with lock:
                payload = dict(car, **status)
                payload['sensors'] = sensors(car['x'], car['y'], car['heading'])
                payload['angles'] = ANGLES
                payload['lap'] = round(100 * max(0, car['travel']) / PERIMETER, 1)
            data, kind = json.dumps(payload).encode(), 'application/json'
        elif self.path in ('/', '/index.html'):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    threading.Thread(target=train, daemon=True).start()
    threading.Thread(target=animate, daemon=True).start()
    print(f'Demo: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
