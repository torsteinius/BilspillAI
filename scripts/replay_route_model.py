"""View frozen route-model choices and autonomous runs on saved training mazes."""
import argparse
from collections import Counter
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from games.maze.history import decode_bits
from games.maze.training import Trainer
from games.maze.world import Maze


def build_replays(model, dataset, per_size=2):
    trainer = Trainer.load(model)
    width = trainer.network.architecture[0]
    row_width = 2 if trainer.config.history_action_memory_steps else 4 + 2 * trainer.config.history_choice_memory
    counts = Counter()
    routes = []
    with (Path(dataset) / 'successful-routes.jsonl').open() as stream:
        for line in stream:
            route = json.loads(line)
            size = (route['width'], route['height'])
            if route['split'] != 'train' or counts[size] >= per_size:
                continue
            counts[size] += 1
            routes.append(route)
    replays = []
    variant=trainer.network.metadata.get('training_objective',{}).get('variant',0)
    rng=random.Random(2026102507)
    for route in routes:
        m = route['maze']
        m=dict(m)
        if variant==6:
            pose=rng.choice(route['samples'])['pose']
            m.update(start=[pose['x'],pose['y']],heading=pose['heading'])
        maze = Maze(m['name'], tuple(m['rows']), tuple(m['start']), m['heading'])
        episode = trainer.make_episode(maze)
        frames = [episode.snapshot()]
        while not episode.done and episode.steps < 512:
            values = episode.observations()
            if len(values) > width:
                raise ValueError('Maze exceeds model input capacity')
            episode.apply_outputs(trainer.network.forward(values + [0.] * (width-len(values))))
            frames.append(episode.snapshot())
        choices = []
        for sample in route['samples']:
            values = sample['observation']
            outputs = trainer.network.forward(values + [0.] * (width-len(values)))
            choices.append(dict(predicted=decode_bits(outputs), expected=sample['action'],
                                inputs=values[:4+row_width*sample['history_count']]))
        replays.append(dict(maze=m, attempt=route['attempt'], frames=frames,
                            reference=route['frames'], choices=choices,
                            escaped=episode.escaped, truncated=not episode.done))
    return dict(generation=trainer.network.generation, variant=trainer.network.metadata.get('training_objective',{}).get('variant',
                    4 if trainer.config.history_action_memory_steps else 3 if trainer.config.history_choice_memory else 2),
                memory_row_width=row_width,replays=replays)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8792)
    args = parser.parse_args()
    state = build_replays(args.model, args.dataset)
    document = Path('games/maze/route_view.html').read_bytes()
    payload = json.dumps(state).encode()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                body, kind = document, 'text/html; charset=utf-8'
            elif self.path == '/api/replays':
                body, kind = payload, 'application/json'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    print(json.dumps(dict(rounds=len(state['replays']), escaped=sum(r['escaped'] for r in state['replays']))), flush=True)
    print(f"Variant {state['variant']}: http://127.0.0.1:{args.port}", flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
