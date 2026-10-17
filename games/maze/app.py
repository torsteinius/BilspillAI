"""AI-spill: random maze walker. Run python3 -m games.maze.app."""
import argparse
from dataclasses import fields
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from .training import Config, Trainer
from .world import Rules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', choices=('python', 'mlx-gpu'), default='python')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--model', type=Path, default=Path(__file__).parent / 'models' / 'maze.json')
    parser.add_argument('--generations', type=int, default=60)
    parser.add_argument('--headless', action='store_true', help='Train without a web server')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--resume', action='store_true')
    mode.add_argument('--replay', action='store_true')
    parser.add_argument('--deterministic-history', action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument('--learned-memory', action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument('--start-in-field', action=argparse.BooleanOptionalAction, default=None)
    for name in ('field_stones_step', 'field_stones_max', 'field_size', 'field_stones', 'width', 'height', 'stages', 'seed', 'population', 'train_mazes', 'validation_mazes', 'check_every', 'success_streak'):
        parser.add_argument('--' + name.replace('_', '-'), type=int)
    parser.add_argument('--hidden', type=int, nargs='*')
    for item in fields(Rules):
        if item.name == 'until_failure':
            parser.add_argument('--until-failure', action=argparse.BooleanOptionalAction, default=None)
        else:
            parser.add_argument('--' + item.name.replace('_', '-'), type=int if item.name in ('min_steps', 'max_steps', 'memory_steps') else float)
    args = parser.parse_args()
    rule_values = {item.name: getattr(args, item.name) for item in fields(Rules) if getattr(args, item.name) is not None}
    config_values = {item.name: getattr(args, item.name) for item in fields(Config)
                     if item.name != 'rules' and getattr(args, item.name) is not None}
    try:
        if args.generations < 1:
            raise ValueError('Generations must be positive')
        if args.resume or args.replay:
            if config_values or rule_values:
                raise ValueError('Resume/replay uses the saved rules and configuration; omit configuration flags')
            trainer = Trainer.load(args.model)
        else:
            if args.model.exists():
                raise ValueError('Model already exists. Use --resume, --replay or a new --model filename')
            if config_values.get('deterministic_history'):
                config_values.setdefault('start_in_field', False)
                rule_values.setdefault('revisit_penalty', .05)
                rule_values.setdefault('until_failure', True)
            if config_values.get('learned_memory'):
                config_values.setdefault('start_in_field', False)
                rule_values.setdefault('memory_steps', 40)
                rule_values.setdefault('revisit_penalty', .05)
            trainer = Trainer(Config(**config_values, rules=Rules(**rule_values)), args.model)
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.error(str(error))
    trainer.backend = args.backend
    if args.backend == 'mlx-gpu':
        if not (trainer.config.learned_memory or trainer.config.deterministic_history):
            parser.error('mlx-gpu requires a learned-memory model')
        from ai.mlx_backend import BatchedNetwork
        # Check Metal on the main thread before starting the server or changing a model.
        BatchedNetwork(trainer.network.architecture, [trainer.network.weights]).forward(
            [[[0.] * trainer.network.architecture[0]]])
    if args.headless:
        trainer.replay() if args.replay else trainer.run(args.generations)
        summary = trainer.payload()
        summary.pop('recording')
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != '/api/next':
                self.send_error(404)
                return
            try:
                data = json.dumps(trainer.next_replay(), ensure_ascii=False).encode()
            except ValueError as error:
                self.send_error(409, str(error))
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == '/':
                data, kind = Path(__file__).with_name('history.html' if trainer.config.deterministic_history else 'index.html').read_bytes(), 'text/html; charset=utf-8'
            elif self.path == '/api/state':
                data, kind = json.dumps(trainer.payload(), ensure_ascii=False).encode(), 'application/json'
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

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    if args.replay:
        trainer.replay()
    else:
        threading.Thread(target=trainer.run, args=(args.generations,), daemon=True).start()
    print(f'AI-spill · Labyrint: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
