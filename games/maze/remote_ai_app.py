"""Local maze simulation with evolution and inference served by Studio."""
import argparse
import copy
from dataclasses import replace
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import uuid
from ai_service.client import Client
from .history import HistoryEpisode
from .training import Trainer
from .remote_view import page


class LocalRunner:
    def __init__(self, client, trainer, network_id, generations, population, mazes, record_all=False, record_frames=True):
        if record_all and not record_frames:
            raise ValueError('record_all requires frame recording')
        self.client, self.trainer, self.network_id = client, trainer, network_id
        self.generations, self.population, self.mazes = generations, population, mazes
        self.record_all = record_all
        self.record_frames = record_frames
        self.attempts = []
        self.lock = threading.Lock()
        self.state = trainer.payload()
        self.state.update(phase='ready', generation=0, target=generations, recording=None,
                          recordings=[], attempts_evaluated=0, total_escapes=0, action_counts={},
                          backend='mlx-gpu', evaluations=[], success=None, session_id=None,
                          execution='Local simulation; remote AI', timing_ms={})
        self.session_id = None

    def payload(self):
        with self.lock:
            result = copy.deepcopy(self.state)
            if self.record_all:
                result['escaped_attempts'] = [i + 1 for i, attempt in enumerate(self.attempts) if attempt['escaped']]
            result['network_id'] = self.network_id
            return result

    def attempt(self, index):
        with self.lock:
            if index < 0 or index >= len(self.attempts):
                raise IndexError("Unknown attempt")
            return copy.deepcopy(self.attempts[index])

    def start_session(self):
        session = self.client.create_evolution_session(network_id=self.network_id,
            population_size=self.population, elite_count=min(6,self.population),
            mutation_sigma=.12, seed=42, request_id=str(uuid.uuid4()))
        self.session_id = session['session_id']
        with self.lock:
            self.state['session_id'] = self.session_id

    def check_curriculum(self, checkpoint_id, generation):
        trainer = self.trainer
        # Validation does not participate in selection or mutate the weights.
        count = max(trainer.config.validation_mazes, trainer.config.success_streak)
        mazes = [trainer.fresh_maze('validation') for _ in range(count)]
        episodes = [trainer.make_episode(m) for m in mazes]
        while any(not e.done for e in episodes):
            active = [e for e in episodes if not e.done]
            reply = self.client.predict(self.network_id, [e.observations() for e in active])
            if reply['checkpoint_id'] != checkpoint_id or len(reply['outputs']) != len(active):
                raise RuntimeError('Model changed during curriculum validation')
            for episode, output in zip(active, reply['outputs']):
                episode.apply_outputs(output)
        # Every check uses a single, fixed model and fresh mazes.
        trainer.streak = 0
        for episode in episodes:
            trainer.streak = trainer.streak + 1 if episode.clean_success else 0
            if trainer.streak >= trainer.config.success_streak:
                break
        evaluation = dict(generation=generation, width=trainer.width, height=trainer.height,
            success_rate=sum(e.clean_success for e in episodes)/count, sample_count=count,
            streak=trainer.streak, mazes=[m.name for m in mazes])
        trainer.evaluations.append(evaluation)
        trainer.check_index += 1
        with self.lock:
            self.state.update(evaluations=copy.deepcopy(trainer.evaluations),
                validation_success=evaluation['success_rate'], streak=trainer.streak)
        if trainer.streak < trainer.config.success_streak:
            return False
        exported = self.client.checkpoint(self.network_id)
        if exported['checkpoint_id'] != checkpoint_id:
            raise RuntimeError('Model changed before curriculum growth')
        # Use the actual API winner, never the initial local model's weights.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json'
            path.write_text(json.dumps(exported['checkpoint']))
            from ai.network import NeuralNetwork
            trainer.network = NeuralNetwork.load(path)
        trainer.streak_model = None
        trainer.config = replace(trainer.config, stages=max(trainer.config.stages, trainer.stage+2))
        trainer.model = trainer.model.with_name(f'{trainer.model.stem}-curriculum.json')
        trainer.grow_if_ready()
        trainer._metadata()
        trainer.network.save(trainer.model)
        changed = self.client.replace_checkpoint(self.network_id,
            json.loads(trainer.model.read_text()), checkpoint_id)
        self.start_session()
        with self.lock:
            self.state.update(width=trainer.width, height=trainer.height, stage=trainer.stage+1,
                architecture=list(trainer.network.architecture), streak=0,
                checkpoint_id=changed['checkpoint_id'], curriculum_model=str(trainer.model),
                last_growth=dict(generation=generation, width=trainer.width,height=trainer.height))
        return True

    def run(self):
        try:
            status = self.client.engine_status()
            if status.get('backend') != 'mlx-gpu' or not status.get('metal_available'):
                raise RuntimeError('Studio GPU is not available')
            description = self.client._request('GET', '/v1/networks/' + self.network_id)
            if description['metadata']['architecture'] != list(self.trainer.network.architecture):
                raise ValueError('Local observation architecture differs from Studio model')
            self.start_session()
            with self.lock:
                self.state.update(phase='training', session_id=self.session_id)
            for generation in range(1, self.generations+1):
                started = time.perf_counter()
                asked = self.client.ask(self.session_id, f'ask-{generation}')
                ids = asked['candidate_ids']
                # Same local environments for every candidate, including the incumbent.
                mazes = [self.trainer.fresh_maze('training') for _ in range(self.mazes)]
                episodes = {(cid,str(i)):self.trainer.make_episode(maze)
                            for cid in ids for i,maze in enumerate(mazes)}
                frames = {key:[episode.snapshot()] for key,episode in episodes.items()} if self.record_frames else None
                compute = roundtrip = local = 0.
                sensor_count = self.trainer.config.history_sensor_count
                used_width = sensor_count
                while any(not e.done for e in episodes.values()):
                    tick = time.perf_counter()
                    active = {key:e for key,e in episodes.items() if not e.done}
                    used_width = max(used_width, max(sensor_count * (1 + len(e.memory)) for e in active.values()))
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
                        if frames is not None:
                            frames[key].append(e.snapshot())
                    local += (time.perf_counter()-tick)*1000
                scores = [sum(episodes[cid,str(i)].score for i in range(self.mazes))/self.mazes for cid in ids]
                mask_options = {}
                if 'mutation_active_inputs' in self.trainer.network.metadata:
                    mask_options['used_inputs'] = [i < used_width for i in range(self.trainer.network.architecture[0])]
                result = self.client.tell(self.session_id,asked['generation_id'],scores,
                                         f'tell-{generation}',f'{self.session_id}-mazes-{generation}', **mask_options)
                winner = result['selected_candidate']
                with self.lock:
                    self.state.update(generation=generation,score=result['score'],
                        checkpoint_id=result['checkpoint_id'],
                        timing_ms=dict(studio_compute=compute,ai_roundtrip=roundtrip,
                                       local_simulation=local,total=(time.perf_counter()-started)*1000))
                    self.state['recordings'] = [dict(
                        id=f'{self.session_id}:{generation}:{i}', generation=generation,
                        checkpoint_id=result['checkpoint_id'], candidate=ids.index(winner),
                        maze=maze.payload(), frames=frames[winner,str(i)],
                        score=episodes[winner,str(i)].score, escaped=episodes[winner,str(i)].escaped)
                        for i,maze in enumerate(mazes)] if self.record_frames else []
                    if self.record_all:
                        for ci,cid in enumerate(ids):
                            for mi,maze in enumerate(mazes):
                                episode=episodes[cid,str(mi)]
                                self.attempts.append(dict(id=f'{self.session_id}:{generation}:{ci}:{mi}',
                                    generation=generation,candidate=ci,maze_index=mi,
                                    selected=cid==winner,fitness=scores[ci],score=episode.score,
                                    escaped=episode.escaped,maze=maze.payload(),frames=frames[cid,str(mi)]))
                        self.state['attempt_count']=len(self.attempts)
                    self.state['recording'] = self.state['recordings'][0] if self.state['recordings'] else None
                    self.state['attempts_evaluated'] += len(episodes)
                    self.state['total_escapes'] += sum(e.escaped for e in episodes.values())
                    actions = Counter(self.state['action_counts'])
                    actions.update(a for e in episodes.values() for a in e.actions)
                    self.state['action_counts'] = dict(actions)
                    self.state['success'] = sum(episodes[winner,str(i)].escaped for i in range(self.mazes))/self.mazes
                if generation % self.trainer.config.check_every == 0:
                    self.check_curriculum(result['checkpoint_id'], generation)
                print(json.dumps(dict(generation=generation,session_id=self.session_id,
                                      score=result['score'], total_escapes=self.state['total_escapes'],
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
    p.add_argument('--record-all',action='store_true',help='Replay every candidate/maze attempt in order without skipping')
    p.add_argument('--replay-attempts',type=Path,help='Restore the complete saved attempt queue (JSONL)')
    p.add_argument('--replay-state',type=Path,help='Display a saved completed run without training again')
    p.add_argument('--follow-replay-state',action='store_true',help='Reload an atomically updated replay state on each poll')
    p.add_argument('--training-progress',type=Path,help='Show progress from a separate headless training run')
    args=p.parse_args()
    if args.follow_replay_state and (not args.replay_state or args.record_all):
        p.error('--follow-replay-state requires --replay-state without --record-all')
    if args.replay_attempts and (not args.replay_state or not args.record_all):
        p.error('--replay-attempts requires --replay-state and --record-all')
    if min(args.generations,args.population,args.mazes)<1:p.error('Counts must be positive')
    trainer=Trainer.load(args.model)
    if not trainer.config.deterministic_history:p.error('Requires deterministic history model')
    runner=LocalRunner(Client(args.service),trainer,args.network_id,args.generations,args.population,args.mazes,record_all=args.record_all)
    if args.replay_state:
        saved_state=json.loads(args.replay_state.read_text())
        if saved_state.get('phase') != 'replay':
            p.error('Saved state must be a completed run')
        runner.state=saved_state
        if args.replay_attempts:
            runner.attempts=[json.loads(line) for line in args.replay_attempts.read_text().splitlines() if line.strip()]
            if len(runner.attempts)!=saved_state.get('attempt_count'):
                p.error('Saved attempt count does not match replay state')
    document=page(100).decode().replace('Mac Studio · Trening','MacBook · Studio AI')
    document=document.replace("'Mac Studio · labyrint'", "'MacBook · AI på Studio'")
    document=document.replace('Trening på Studio. Status hentes hvert 10. sekund. Nytt eksisterende opptak velges omtrent hver 100. generasjon og ved avslutning. Animasjonen spilles lokalt og starter ingen ekstra treningsforsøk.', 'Simulering, sensorer og belønning på MacBook. Kandidatnett beregnes på Studio-GPU. Generasjon teller denne økten. Lokalt opptak ved start, hver 100. generasjon og slutt. Labyrintstørrelsen er låst i denne økten.')
    document=document.replace("$('error').textContent=state.error||'';", "$('growth').textContent='Fast labyrintstørrelse i denne økten';$('nextStage').textContent='Lokal simulering';$('error').textContent=state.error||'';")
    document=document.replace('<main>', '<main><div style="padding:12px;background:#15253a;color:white"><label>Labyrint: <select id="mazeChoice"></select></label><span id="liveInfo"> Venter på første generasjon</span></div>')
    document=document.replace("state=await r.json();if(!latest||state.recording?.id>latest.id)latest=state.recording;", """state=await r.json();
const choices=$('mazeChoice'), records=state.recordings||[];
if(choices.options.length!==records.length){choices.replaceChildren(...records.map((r,i)=>new Option(String(i+1),String(i))));}
const selected=records[Number(choices.value)||0];
if(selected){latest=selected;if(!recording||recording.id!==selected.id){shownLayouts=[];adopt(selected);lastEnd=0;}
$('liveInfo').textContent=' · Øktgenerasjon '+selected.generation+' · Modell '+selected.checkpoint_id.slice(0,12);}
""")
    document=document.replace("$('next').onclick=nextMaze;", "$('next').onclick=nextMaze;$('mazeChoice').onchange=()=>{const r=state?.recordings?.[Number($('mazeChoice').value)];if(r){shownLayouts=[];latest=r;adopt(r);lastEnd=0;}};")
    document=document.replace('setTimeout(poll,10000)', 'setTimeout(poll,1000)')
    document=document.replace('Lokalt opptak ved start, hver 100. generasjon og slutt.', 'Visningen følger siste fullførte generasjon. Velg labyrint øverst.')
    if args.record_all:
        start=document.index("const choices=$('mazeChoice')")
        end=document.index("$('phase').textContent",start)
        document=document[:start]+"""
if(queueSession!==state.session_id){queueSession=state.session_id;queueIndex=requestedAttempt===null?0:requestedAttempt-1;recording=null;latest=null;}
if(queueIndex>=(state.attempt_count||0) && state.phase==='replay')throw Error('Dette forsøket finnes ikke i denne kjøringen');
const successes=state.escaped_attempts||[];
$('replayTitle').textContent=state.run_kind==='evaluation'?(state.generation===0?'Ny, utrent modell · testvisning':'Samme nettverk på forskjellige labyrinter'):'Opptak fra treningen';
$('attemptSummary').textContent=state.attempt_count+(state.run_kind==='evaluation'?' testlabyrinter':' treningsforsøk')+' · '+successes.length+' nådde utgangen. '+(requestedAttempt===null?'Viser alle i rekkefølge fra forsøk 1.':'Viser kun valgt forsøk; stopper på siste steg.');
$('successLinks').replaceChildren(...successes.map(n=>{const a=document.createElement('a');a.href='?attempt='+n;a.textContent='Vis forsøk '+n;a.style.marginRight='16px';return a;}));
if(!recording && queueIndex<(state.attempt_count||0)){
 const response=await fetch('/api/attempts/'+queueIndex);if(!response.ok)throw Error('Missing attempt');
 const item=await response.json();shownLayouts=[];adopt(item);latest=item;lastEnd=0;
}
"""+document[end:]
        document=document.replace("let latest=null,", "const attemptParam=Number(new URLSearchParams(location.search).get('attempt'));const requestedAttempt=Number.isInteger(attemptParam)&&attemptParam>0?attemptParam:null;let queueIndex=0,queueSession=null;let latest=null,")
        document=document.replace("function nextMaze(){if(recording){frameIndex=0;lastEnd=0;draw()}}", "function nextMaze(){if(requestedAttempt!==null)return;if(recording && frameIndex===recording.frames.length-1 && queueIndex+1<(state?.attempt_count||0)){queueIndex++;recording=null;latest=null;lastEnd=0;}}")
        document=document.replace("$('next').disabled=!recording", "$('next').disabled=true")
        document=document.replace('<label>Labyrint: <select id="mazeChoice"></select></label>', '<select id="mazeChoice" hidden></select><strong id="replayTitle">Opptak fra treningen</strong><p id="attemptSummary"></p><p id="successLinks"></p><a href="?view=all-attempts">Spill alle fra starten</a> · <button id="replayAttempt" type="button">Spill dette forsøket på nytt</button><br>')
        document=document.replace("$('next').onclick=nextMaze;", "$('replayAttempt').onclick=()=>{frameIndex=0;lastEnd=0;paused=false;$('pause').textContent='Pause visning';draw();};$('next').onclick=nextMaze;")
        document=document.replace('Visningen følger siste fullførte generasjon. Velg labyrint øverst.', 'Alle kandidater og labyrinter spilles i rekkefølge. Treningen kan ligge foran avspillingen; ingen opptak hoppes over.')
    if args.record_all:
        document=document.replace("$('phase').textContent=phases[state.phase]||state.phase;", "")
        document=document.replace("function draw(){if(!recording)return;", "function draw(){if(!recording){ctx.clearRect(0,0,900,900);$('best').textContent='—';$('score').textContent='—';$('reward').textContent='—';$('success').textContent='Laster';$('liveInfo').textContent=' Henter forsøk '+(queueIndex+1)+' / '+(state?.attempt_count||0);$('event').textContent='Henter neste opptak';return;}")
        document=document.replace("$('event').textContent=f.event;", "$('phase').textContent=(f.done && queueIndex+1===(state?.attempt_count||0) && state?.phase==='replay')?'Alle forsøk er ferdig avspilt':paused?'Avspilling pauset':'Spiller forsøk '+(queueIndex+1)+' / '+(state?.attempt_count||0);$('liveInfo').textContent=' Forsøk '+(queueIndex+1)+' / '+state.attempt_count+' · Generasjon '+recording.generation+' · Kandidat '+(recording.candidate+1)+' · Labyrint '+(recording.maze_index+1)+' · Steg '+f.steps+' · Poeng nå '+f.score.toFixed(2);$('event').textContent=f.event;")
    # Replay statistics must come from the frame on the canvas, not a newer generation.
    if args.record_all:
        document=document.replace("(f.done && queueIndex+1===(state?.attempt_count||0) && state?.phase==='replay')", "(f.done && (requestedAttempt!==null || queueIndex+1===(state?.attempt_count||0)) && state?.phase==='replay')")
        document=document.replace("?'Alle forsøk er ferdig avspilt'", "?(requestedAttempt!==null?'Valgt forsøk er ferdig avspilt':'Alle forsøk er ferdig avspilt')")
    document=document.replace('Beste treningspoeng', 'Poeng i vist forsøk nå')
    document=document.replace('Feilfri · nye forsøk', 'Status i vist forsøk')
    document=document.replace('Område under trening', 'Område som vises')
    document=document.replace('<span>Generasjon</span>', '<span>Generasjon som vises</span>')
    document=document.replace("$('best').textContent=state.score==null?'—':state.score.toFixed(1);", '')
    document=document.replace("$('success').textContent=state.success==null?'—':Math.round(100*state.success)+' %';", '')
    document=document.replace("$('generation').textContent=state.generation+(state.target?' / '+state.target:'');", '')
    document=document.replace("$('size').textContent=state.width+' × '+state.height+(state.environment==='field'?' · '+state.field_stones+' bokser':'');", '')
    document=document.replace("$('event').textContent=f.event;", "$('best').textContent=f.score.toFixed(2);$('generation').textContent=recording.generation;$('size').textContent=m.width+' × '+m.height;$('success').textContent=f.escaped?'Fant utgangen':f.done?'Avsluttet':'Pågår';$('event').textContent=f.event;")
    document=document.replace(" · Poeng '+recording.score.toFixed(2)", " · Sluttpoeng '+recording.score.toFixed(2)")
    document=document.replace(" · Poeng '+selected.score.toFixed(2)", " · Sluttpoeng '+selected.score.toFixed(2)")
    if args.follow_replay_state:
        document=document.replace("$('event').textContent=f.event;", "$('phase').textContent=state.training_phase==='training'?'Trener: '+state.training_generation+' / '+state.training_target:'Trening ferdig';$('liveInfo').textContent=' · Viser runde '+recording.generation+' · Labyrint '+(Number($('mazeChoice').value)+1)+' · Steg '+f.steps+' · Poeng nå '+f.score.toFixed(2)+' · Oppdateres hver 300. runde';$('event').textContent=f.event;")
        document=document.replace('Visningen følger siste fullførte generasjon. Velg labyrint øverst.', 'Visningen oppdateres hver 300. runde og ved avslutning. Velg mellom de to labyrintene. Treningen fortsetter uavhengig av avspillingen.')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split('?')[0]=='/':data,kind=document.encode(),'text/html; charset=utf-8'
            elif self.path=='/api/state':
                if args.follow_replay_state:
                    payload=json.loads(args.replay_state.read_text())
                    if args.training_progress:
                        progress=json.loads(args.training_progress.read_text())
                        payload.update(training_generation=progress['generation'],training_target=progress['target'],training_phase=progress['phase'])
                else:
                    payload=runner.payload()
                data,kind=json.dumps(payload).encode(),'application/json'
            elif self.path.startswith('/api/attempts/'):
                try:data,kind=json.dumps(runner.attempt(int(self.path.rsplit('/',1)[-1]))).encode(),'application/json'
                except (ValueError,IndexError):self.send_error(404);return
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
            self.end_headers();self.wfile.write(data)
        def log_message(self,*_):pass
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    if not args.replay_state:
        threading.Thread(target=runner.run,daemon=True).start()
    print(f'Local simulator: http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()


if __name__=='__main__':main()
