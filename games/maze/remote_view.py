"""Read-only Studio training viewer; animation runs locally from saved recordings."""
import argparse
import copy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.request import urlopen


class Snapshot:
    def __init__(self, every=100):
        self.every = every
        self.bucket = None
        self.recording = None
        self.state = None
        self.finished = False

    def update(self, run):
        state = copy.deepcopy(run['progress'])
        generation = state['generation']
        finished = run['state'] in ('completed', 'stopped', 'failed')
        candidate = state.get('recording')
        bucket = generation // self.every
        if candidate and (self.recording is None or bucket != self.bucket or finished != self.finished):
            self.recording = candidate
            self.bucket = bucket
        self.finished = finished
        state['recording'] = self.recording
        state['target'] = run['target_generation']
        state['error'] = run.get('error') or state.get('error')
        state['phase'] = {'completed': 'replay', 'stopped': 'stopped', 'failed': 'error'}.get(run['state'], state['phase'])
        state['remote_every'] = self.every
        self.state = state
        return state


def page(every):
    html = Path(__file__).with_name('history.html').read_text()
    html = html.replace('<title>AI-spill · Labyrint</title>', '<title>Mac Studio · Trening</title>')
    html = html.replace('Neste labyrint</button>', 'Spill opptaket igjen</button>')
    html = html.replace("$('next').disabled=state.phase!=='replay'||loadingNext", "$('next').disabled=!recording")
    start = html.index('async function nextMaze()')
    end = html.index("$('next').onclick=nextMaze;", start)
    html = html[:start] + "function nextMaze(){if(recording){frameIndex=0;lastEnd=0;draw()}}\n" + html[end:]
    html = html.replace("else if(state?.phase==='replay'){nextMaze()}", 'else {nextMaze()}')
    html = html.replace("$('error').textContent=state.error||'';", "$('error').textContent=state.error||'';$('environment').textContent='Mac Studio · labyrint';document.querySelector('main > p.label').textContent='Trening på Studio. Status hentes hvert 10. sekund. Nytt eksisterende opptak velges omtrent hver "+str(every)+". generasjon og ved avslutning. Animasjonen spilles lokalt og starter ingen ekstra treningsforsøk.';")
    return html.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--service', default='http://127.0.0.1:8780')
    parser.add_argument('--port', type=int, default=8775)
    parser.add_argument('--every', type=int, default=100)
    args = parser.parse_args()
    if args.every < 1:
        parser.error('--every must be positive')
    snapshot = Snapshot(args.every)
    lock = threading.Lock()
    stop = threading.Event()
    error = 'Venter på forbindelse til Studio'

    def refresh():
        nonlocal error
        while not stop.is_set():
            try:
                with urlopen(args.service.rstrip('/') + '/training-runs/' + args.run_id, timeout=5) as response:
                    run = json.load(response)
                with lock:
                    snapshot.update(run)
                    error = None
            except Exception as exc:
                with lock:
                    error = 'Studio utilgjengelig: ' + str(exc)
            stop.wait(10)

    document = page(args.every)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                data, kind, status = document, 'text/html; charset=utf-8', 200
            elif self.path == '/api/state':
                with lock:
                    payload = dict(snapshot.state) if snapshot.state else {'error': error}
                    if error:
                        payload['error'] = error
                    status = 200 if snapshot.state else 503
                data, kind = json.dumps(payload).encode(), 'application/json'
            else:
                self.send_error(404)
                return
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)
        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    threading.Thread(target=refresh, daemon=True).start()
    print(f'Studio-visning: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
