"""Local maze simulation with evolution and inference served by Studio."""
import argparse
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
import uuid
from ai_service.client import Client
from .history import HistoryEpisode
from .training import Trainer
from .remote_view import page


class LocalRunner:
    def __init__(self, client, trainer, network_id, generations, population, mazes):
        self.client, self.trainer, self.network_id = client, trainer, network_id
        self.generations, self.population, self.mazes = generations, population, mazes
        self.lock = threading.Lock()
        self.state = trainer.payload()
        self.state.update(phase='ready', generation=0, target=generations, recording=None,
                          backend='mlx-gpu', evaluations=[], success=None, session_id=None,
                          execution='Local simulation; remote AI', timing_ms={})
        self.session_id = None

    def payload(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def run(self):
        try:
            status = self.client.engine_status()
            if status.get('backend') != 'mlx-gpu' or not status.get('metal_available'):
                raise RuntimeError('Studio GPU is not available')
            description = self.client._request('GET', '/v1/networks/' + self.network_id)
            if description['metadata']['architecture'] != list(self.trainer.network.architecture):
                raise ValueError('Local observation architecture differs from Studio model')
            session = self.client.create_evolution_session(network_id=self.network_id,
                population_size=self.population, elite_count=min(6,self.population),
                mutation_sigma=.12, seed=42, request_id=str(uuid.uuid4()))
            self.session_id = session['session_id']
            with self.lock:
                self.state.update(phase='training', session_id=self.session_id)
            for generation in range(1, self.generations+1):
                started = time.perf_counter()
                asked = self.client.ask(self.session_id, f'ask-{generation}')
                ids = asked['candidate_ids']
                # Same local environments for every candidate, including the incumbent.
                mazes = [self.trainer.fresh_maze('training') for _ in range(self.mazes)]
                episodes = {(cid,str(i)):HistoryEpisode(maze,self.trainer.config.rules)
                            for cid in ids for i,maze in enumerate(mazes)}
                record = generation == 1 or generation % 100 == 0 or generation == self.generations
                frames = {cid:[episodes[cid,'0'].snapshot()] for cid in ids} if record else {}
                compute = roundtrip = local = 0.
                while any(not e.done for e in episodes.values()):
                    tick = time.perf_counter()
                    active = {key:e for key,e in episodes.items() if not e.done}
                    items = [dict(candidate_id=cid,sample_id=sid,input=e.observations())
                             for (cid,sid),e in active.items()]
                    local += (time.perf_counter()-tick)*1000
                    tick = time.perf_counter()
                    reply = self.client.candidate_predict(self.session_id,asked['generation_id'],items)
                    roundtrip += (time.perf_counter()-tick)*1000
                    if reply.get('backend') != 'mlx-gpu':
                        raise RuntimeError('Studio did not confirm GPU inference')
                    compute += reply.get('timing_ms',{}).get('model_compute_wall',0)
                    returned = {(r['candidate_id'],r['sample_id']):r['output'] for r in reply['items']}
                    if set(returned) != set(active) or len(reply['items']) != len(active):
                        raise ValueError('Studio returned mismatched episode IDs')
                    tick = time.perf_counter()
                    for key,e in active.items():
                        e.apply_outputs(returned[key])
                        if record and key[1]=='0': frames[key[0]].append(e.snapshot())
                    local += (time.perf_counter()-tick)*1000
                scores = [sum(episodes[cid,str(i)].score for i in range(self.mazes))/self.mazes for cid in ids]
                result = self.client.tell(self.session_id,asked['generation_id'],scores,
                                         f'tell-{generation}',f'{self.session_id}-mazes-{generation}')
                winner = result['selected_candidate']
                with self.lock:
                    self.state.update(generation=generation,score=result['score'],
                        checkpoint_id=result['checkpoint_id'],
                        timing_ms=dict(studio_compute=compute,ai_roundtrip=roundtrip,
                                       local_simulation=local,total=(time.perf_counter()-started)*1000))
                    if record:
                        self.state['recording']=dict(id=generation,generation=generation,
                            candidate=ids.index(winner),maze=mazes[0].payload(),frames=frames[winner])
                print(json.dumps(dict(generation=generation,session_id=self.session_id,
                                      timing_ms=self.state['timing_ms'])),flush=True)
            with self.lock: self.state['phase']='replay'
        except Exception as exc:
            with self.lock: self.state.update(phase='error',error=str(exc))
            import traceback
            traceback.print_exc()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--service',default='http://127.0.0.1:8780')
    p.add_argument('--network-id',default='maze-history-api-v1')
    p.add_argument('--model',type=Path,default=Path('games/maze/models/deterministic_history_v1.json'))
    p.add_argument('--generations',type=int,default=2)
    p.add_argument('--population',type=int,default=4)
    p.add_argument('--mazes',type=int,default=2)
    p.add_argument('--port',type=int,default=8776)
    args=p.parse_args()
    if min(args.generations,args.population,args.mazes)<1:p.error('Counts must be positive')
    trainer=Trainer.load(args.model)
    if not trainer.config.deterministic_history:p.error('Requires deterministic history model')
    runner=LocalRunner(Client(args.service),trainer,args.network_id,args.generations,args.population,args.mazes)
    document=page(100).decode().replace('Mac Studio · Trening','MacBook · Studio AI')
    document=document.replace("'Mac Studio · labyrint'", "'MacBook · AI på Studio'")
    document=document.replace('Trening på Studio. Status hentes hvert 10. sekund. Nytt eksisterende opptak velges omtrent hver 100. generasjon og ved avslutning. Animasjonen spilles lokalt og starter ingen ekstra treningsforsøk.', 'Simulering, sensorer og belønning på MacBook. Kandidatnett beregnes på Studio-GPU. Generasjon teller denne økten. Lokalt opptak ved start, hver 100. generasjon og slutt. Labyrintstørrelsen er låst i denne økten.')
    document=document.replace("$('error').textContent=state.error||'';", "$('growth').textContent='Fast labyrintstørrelse i denne økten';$('nextStage').textContent='Lokal simulering';$('error').textContent=state.error||'';")
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/':data,kind=document.encode(),'text/html; charset=utf-8'
            elif self.path=='/api/state':data,kind=json.dumps(runner.payload()).encode(),'application/json'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(data)
        def log_message(self,*_):pass
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    threading.Thread(target=runner.run,daemon=True).start()
    print(f'Local simulator: http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()


if __name__=='__main__':main()
