"""Replay the latest API checkpoint on both mazes from a selected local generation."""
import argparse
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ai_service.client import Client
from games.maze.training import Trainer
from games.maze.history import HistoryEpisode
from games.maze.remote_view import page


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--service',default='http://127.0.0.1:8787')
    p.add_argument('--network-id',default='history-5-normalized-v1')
    p.add_argument('--model',type=Path,default=Path('.ai-service/history-5-normalized.json'))
    p.add_argument('--generation',type=int,default=50)
    p.add_argument('--port',type=int,default=8788)
    args=p.parse_args()
    trainer=Trainer.load(args.model);client=Client(args.service)
    description=client._request('GET','/v1/networks/'+args.network_id)
    checkpoint=description['checkpoint_id']
    for _ in range(args.generation):
        mazes=[trainer.fresh_maze('training') for _ in range(2)]
    episodes=[trainer.make_episode(m) for m in mazes]
    frames=[[e.snapshot()] for e in episodes]
    while any(not e.done for e in episodes):
        active=[i for i,e in enumerate(episodes) if not e.done]
        reply=client.predict(args.network_id,[episodes[i].observations() for i in active])
        if reply['checkpoint_id']!=checkpoint:
            raise RuntimeError('Checkpoint changed during replay; rerun to keep a single model')
        for i,output in zip(active,reply['outputs']):
            episodes[i].apply_outputs(output);frames[i].append(episodes[i].snapshot())
    recordings=[dict(id=f'{checkpoint}:{i}',generation=args.generation,candidate=0,
                     maze=m.payload(),frames=frames[i]) for i,m in enumerate(mazes)]
    state=trainer.payload()
    state.update(phase='replay',generation=args.generation,target=args.generation,
                 score=sum(e.score for e in episodes)/len(episodes),success=sum(e.escaped for e in episodes)/len(episodes),
                 backend='mlx-gpu',checkpoint_id=checkpoint,network_id=args.network_id,
                 recordings=recordings,recording=recordings[0],error=None)
    state['results']=[dict(score=e.score,escaped=e.escaped,steps=e.steps) for e in episodes]
    Path('.ai-service/latest-model-replay.json').write_text(json.dumps(state))
    html=page(100).decode()
    html=html.replace('<main>', '<main><div style="padding:16px;background:#15253a;color:white">Siste lagrede nettverk · '+args.network_id+'<br>Checkpoint: '+checkpoint+'<br><label>Vis labyrint: <select id="mazeChoice"><option value="0">1</option><option value="1" selected>2</option></select></label><span id="replayResult"></span></div>')
    old="state=await r.json();if(!latest||state.recording?.id>latest.id)latest=state.recording;"
    new="""state=await r.json();const choice=Number($('mazeChoice').value);state.recording=state.recordings[choice];
const result=state.results[choice];$('replayResult').textContent=' · Poeng: '+result.score.toFixed(2)+' · '+(result.escaped?'Fant utgangen':'Fant ikke utgangen')+' · '+result.steps+' steg';
if(!latest||state.recording.id!==latest.id){shownLayouts=[];latest=state.recording;adopt(latest);lastEnd=0;}"""
    if old not in html:raise RuntimeError('Viewer polling template changed')
    html=html.replace(old,new)
    html=html.replace("$('next').onclick=nextMaze;", "$('next').onclick=nextMaze;$('mazeChoice').onchange=()=>poll();")
    html=html.replace('Trening på Studio. Status hentes hvert 10. sekund. Nytt eksisterende opptak velges omtrent hver 100. generasjon og ved avslutning. Animasjonen spilles lokalt og starter ingen ekstra treningsforsøk.', 'Begge labyrintene er kjørt på nytt gjennom API-et med samme siste checkpoint. Velg labyrint over. Dette er avspilling; ingen trening pågår.')
    data=html.encode()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/':body,kind=data,'text/html; charset=utf-8'
            elif self.path=='/api/state':body,kind=json.dumps(state).encode(),'application/json'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    print(json.dumps(dict(checkpoint_id=checkpoint,results=state['results'],mean_score=state['score'])),flush=True)
    print(f'Replay: http://127.0.0.1:{args.port}/',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

if __name__=='__main__':main()
