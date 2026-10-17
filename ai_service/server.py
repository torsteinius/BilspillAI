"""HTTP service for the deterministic maze checkpoint.

Run locally with ``python -m ai_service.server``.  It intentionally uses only
the standard library; MLX remains an engine dependency, not an HTTP dependency.
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import shutil
import sqlite3
import sys
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / 'games/maze/models/deterministic_history_v1.json'
DEFAULT_DETECTOR = ROOT / 'games/maze/history_detector.json'

def now(): return datetime.now(timezone.utc).isoformat()
def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

class Store:
    def __init__(self, home):
        self.home = Path(home); self.home.mkdir(parents=True, exist_ok=True)
        self.db = self.home / 'registry.sqlite3'
        with self.connect() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS networks (network_id TEXT PRIMARY KEY, app_id TEXT NOT NULL,
                checkpoint TEXT NOT NULL, detector TEXT NOT NULL, metadata TEXT NOT NULL, imported_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, network_id TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL, start_generation INTEGER NOT NULL, target_generation INTEGER NOT NULL,
                checkpoint TEXT NOT NULL, progress TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            ''')
            # A process cannot survive an API restart.  Never falsely report it running.
            db.execute("UPDATE runs SET state='failed', error='API restarted while job was active', updated_at=? WHERE state IN ('running','stopping')", (now(),))
    def connect(self):
        db = sqlite3.connect(self.db, timeout=10); db.row_factory = sqlite3.Row; return db
    def network(self, network_id):
        with self.connect() as db: return db.execute('SELECT * FROM networks WHERE network_id=?', (network_id,)).fetchone()
    def run(self, run_id):
        with self.connect() as db: return db.execute('SELECT * FROM runs WHERE run_id=?', (run_id,)).fetchone()
    def run_by_request(self, request_id):
        with self.connect() as db: return db.execute('SELECT * FROM runs WHERE request_id=?', (request_id,)).fetchone()

def row_json(row):
    result = dict(row)
    for field in ('metadata', 'progress'):
        if field in result: result[field] = json.loads(result[field])
    return result

def worker(service_home, run_id, stop_event):
    """Separate process: an MLX failure cannot take down the HTTP server."""
    store = Store(service_home)
    row = store.run(run_id)
    try:
        from games.maze.training import Trainer
        trainer = Trainer.load(row['checkpoint']); trainer.backend = 'mlx-gpu'
        def report(payload):
            with store.connect() as db:
                db.execute('UPDATE runs SET progress=?, updated_at=? WHERE run_id=?',
                           (json.dumps(payload), now(), run_id))
        with store.connect() as db:
            db.execute("UPDATE runs SET state='running', updated_at=? WHERE run_id=?", (now(), run_id))
        report(trainer.payload())
        completed = trainer.run(row['target_generation'] - row['start_generation'], stop_event=stop_event, progress_callback=report)
        with store.connect() as db:
            db.execute("UPDATE runs SET state=?, progress=?, updated_at=? WHERE run_id=?",
                       ('completed' if completed else 'stopped', json.dumps(trainer.payload()), now(), run_id))
            if completed:
                # The immutable run copy becomes the next explicit continuation point.
                db.execute('UPDATE networks SET checkpoint=? WHERE network_id=?', (row['checkpoint'], row['network_id']))
    except Exception as error:
        with store.connect() as db:
            db.execute("UPDATE runs SET state='failed', error=?, updated_at=? WHERE run_id=?",
                       (str(error), now(), run_id))
        traceback.print_exc()

class Service:
    def __init__(self, home):
        self.store, self.active = Store(home), None
        from ai_service.generic import GenericAPI
        self.generic = GenericAPI(home)
    def import_default(self, network_id='maze-history-v1'):
        if self.store.network(network_id): return row_json(self.store.network(network_id))
        from games.maze.training import Trainer
        trainer = Trainer.load(DEFAULT_MODEL)  # validates metadata, architecture and weights
        if not DEFAULT_DETECTOR.is_file(): raise ValueError('Frozen history detector is missing')
        target = self.store.home / 'networks' / network_id; target.mkdir(parents=True, exist_ok=True)
        checkpoint, detector = target / 'imported.json', target / 'history_detector.json'
        shutil.copy2(DEFAULT_MODEL, checkpoint); shutil.copy2(DEFAULT_DETECTOR, detector)
        meta = dict(type='dense-tanh-evolution', architecture=list(trainer.network.architecture),
                    observation_version=trainer.network.metadata['observation_version'], actions=['forward','backward','right','left'],
                    adapter='maze', trainer='games.maze.training.Trainer', dependency=dict(path=str(detector), sha256=digest(detector)),
                    source=dict(path=str(DEFAULT_MODEL), sha256=digest(DEFAULT_MODEL)))
        with self.store.connect() as db:
            db.execute('INSERT INTO networks VALUES (?,?,?,?,?,?)', (network_id, 'maze', str(checkpoint), str(detector), json.dumps(meta), now()))
        return row_json(self.store.network(network_id))
    def start(self, body):
        network_id, request_id = body.get('network_id'), body.get('request_id')
        generations = body.get('additional_generations')
        if not isinstance(network_id, str) or not network_id or not isinstance(request_id, str) or not request_id:
            raise ValueError('network_id and request_id must be non-empty strings')
        if type(generations) is not int or not 1 <= generations <= 1000000: raise ValueError('additional_generations must be an integer from 1 to 1000000')
        old = self.store.run_by_request(request_id)
        if old: return row_json(old), False
        network = self.store.network(network_id)
        if not network: raise LookupError('Unknown network_id')
        if self.active and self.active.is_alive(): raise RuntimeError('A GPU training job is already active')
        from games.maze.training import Trainer
        base = Path(network['checkpoint']); trainer = Trainer.load(base)
        run_id = str(uuid.uuid4()); run_dir = self.store.home / 'runs' / run_id; run_dir.mkdir(parents=True)
        checkpoint = run_dir / 'checkpoint.json'; shutil.copy2(base, checkpoint)
        record = dict(run_id=run_id, network_id=network_id, request_id=request_id, state='queued', start_generation=trainer.network.generation,
                      target_generation=trainer.network.generation + generations, checkpoint=str(checkpoint), progress=trainer.payload(), error=None, created_at=now(), updated_at=now())
        with self.store.connect() as db:
            db.execute('INSERT INTO runs VALUES (:run_id,:network_id,:request_id,:state,:start_generation,:target_generation,:checkpoint,:progress,:error,:created_at,:updated_at)', {**record, 'progress':json.dumps(record['progress'])})
        self.stop_event = mp.Event(); self.active = mp.Process(target=worker, args=(str(self.store.home), run_id, self.stop_event), daemon=True); self.active.start()
        return row_json(self.store.run(run_id)), True

def handler(service):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, code, value):
            data = json.dumps(value, ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
        def body(self):
            length = int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(length))
        def do_GET(self):
            parsed=urlparse(self.path); parts=parsed.path.strip('/').split('/')
            try:
                if parsed.path == '/v1/status': return self.respond(200, service.generic.status())
                if len(parts)==3 and parts[:2] == ['v1','networks']:
                    return self.respond(200, service.generic.describe(parts[2]))
                if parsed.path == '/networks':
                    with service.store.connect() as db: return self.respond(200, [row_json(r) for r in db.execute('SELECT * FROM networks')])
                if len(parts)==2 and parts[0]=='training-runs':
                    run=service.store.run(parts[1])
                    return self.respond(200, row_json(run)) if run else self.respond(404, {'error':'Unknown run'})
                if len(parts)==3 and parts[0]=='training-runs' and parts[2]=='recording':
                    run=service.store.run(parts[1]);
                    if not run: return self.respond(404,{'error':'Unknown run'})
                    return self.respond(200, json.loads(run['progress']).get('recording'))
                if len(parts)==3 and parts[0]=='networks' and parts[2]=='checkpoint':
                    n=service.store.network(parts[1]);
                    if not n: return self.respond(404,{'error':'Unknown network'})
                    return self.respond(200, json.loads(Path(n['checkpoint']).read_text()))
                self.respond(404, {'error':'Not found'})
            except Exception as error: self.respond(500, {'error':str(error)})
        def do_POST(self):
            parsed=urlparse(self.path); parts=parsed.path.strip('/').split('/')
            try:
                body=self.body()
                if parsed.path == '/v1/networks/import-legacy':
                    return self.respond(201, service.generic.clone_legacy(body.get('network_id'), body.get('source_checkpoint'), body.get('app_id','maze')))
                if len(parts)==4 and parts[:2] == ['v1','networks'] and parts[3] == 'predict':
                    return self.respond(200, service.generic.predict(parts[2], body))
                if parsed.path == '/v1/evolution/sessions': return self.respond(201, service.generic.create_session(body))
                if len(parts)==5 and parts[:3] == ['v1','evolution','sessions'] and parts[4] == 'ask': return self.respond(200, service.generic.ask(parts[3],body))
                if len(parts)==5 and parts[:3] == ['v1','evolution','sessions'] and parts[4] == 'predict': return self.respond(200, service.generic.candidate_predict(parts[3],body))
                if len(parts)==5 and parts[:3] == ['v1','evolution','sessions'] and parts[4] == 'tell': return self.respond(200, service.generic.tell(parts[3],body))
                if parsed.path == '/networks': return self.respond(201, service.import_default(body.get('network_id','maze-history-v1')))
                if parsed.path == '/training-runs':
                    run, created=service.start(body); return self.respond(201 if created else 200, run)
                if len(parts)==3 and parts[0]=='training-runs' and parts[2]=='stop':
                    if not service.active or not service.active.is_alive(): return self.respond(409, {'error':'No active training job'})
                    if not service.store.run(parts[1]): return self.respond(404, {'error':'Unknown run'})
                    service.stop_event.set()
                    with service.store.connect() as db: db.execute("UPDATE runs SET state='stopping', updated_at=? WHERE run_id=?", (now(),parts[1]))
                    return self.respond(202, row_json(service.store.run(parts[1])))
                self.respond(404, {'error':'Not found'})
            except (ValueError, json.JSONDecodeError) as error: self.respond(400, {'error':str(error)})
            except LookupError as error: self.respond(404, {'error':str(error)})
            except RuntimeError as error: self.respond(409, {'error':str(error)})
            except Exception as error: self.respond(500, {'error':str(error)})
        def log_message(self, *_): pass
    return Handler

def main():
    p=argparse.ArgumentParser(); p.add_argument('--port',type=int,default=8780); p.add_argument('--data-dir',type=Path,default=ROOT/'.ai-service'); args=p.parse_args()
    service=Service(args.data_dir); server=ThreadingHTTPServer(('127.0.0.1',args.port), handler(service)); print(f'AI service: http://127.0.0.1:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__ == '__main__': main()
