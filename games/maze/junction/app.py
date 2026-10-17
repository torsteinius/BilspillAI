"""Show frozen legacy movement and an independent learned stop detector."""
import argparse
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
import mlx.core as mx
from ..training import Trainer
from ..generator import generate
from .model import JunctionDetector
from .task import walk,is_landmark,stop_reward


def recording(walker,detector,seed,size):
    maze=generate(size,size,seed=seed)
    samples,episode=walk(walker,maze)
    probabilities=detector(mx.array([s['rays'] for s in samples])).tolist()
    score=0.
    for s,p in zip(samples,probabilities):
        s['stop']=p>.5;s['stop_probability']=p
        s['reward']=stop_reward(s['stop'],s['kind']);score+=s['reward'];s['detector_score']=score
    samples.append(dict(x=episode.x,y=episode.y,heading=episode.heading,step=episode.steps,
                        rays=[min(v,10.)/10. for v in episode.sensors()],kind='slutt',
                        stop=False,stop_probability=None,reward=0.,detector_score=score,action=None))
    return dict(maze=maze.payload(),frames=samples,escaped=episode.escaped,event=episode.event)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',type=Path,default=Path('games/maze/models/junction_detector_v1'))
    p.add_argument('--port',type=int,default=8772)
    args=p.parse_args();mx.set_default_device(mx.gpu)
    walker=Trainer.load(args.model/'walker.json')
    detector=JunctionDetector();detector.load_weights(str(args.model/'detector.safetensors'))
    mx.eval(detector.parameters())
    state=dict(report=json.loads((args.model/'report.json').read_text()))
    index=0
    def new(size=15):
        nonlocal index
        if size not in (5,9,15):raise ValueError('Invalid size')
        index+=1
        state['recording']=recording(walker,detector,96000000+index,size)
        state['recording']['id']=index
        return state
    new()
    class Handler(BaseHTTPRequestHandler):
        def reply(self,data,kind='application/json'):
            if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path=='/':self.reply(Path(__file__).with_name('index.html').read_bytes(),'text/html; charset=utf-8')
            elif self.path=='/api/state':self.reply(state)
            else:self.send_error(404)
        def do_POST(self):
            if self.path!='/api/next':self.send_error(404);return
            try:
                body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
                self.reply(new(int(body.get('size',15))))
            except (ValueError,TypeError):self.send_error(400)
        def log_message(self,*_):pass
    print(f'Kryssdetektor: http://127.0.0.1:{args.port}',flush=True)
    HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
