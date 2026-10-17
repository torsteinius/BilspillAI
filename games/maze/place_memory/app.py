"""Teleport demonstration: answer first, then write if detector fires."""
import argparse
import json
from pathlib import Path
import random
from http.server import BaseHTTPRequestHandler,HTTPServer
import mlx.core as mx
from ..junction.model import JunctionDetector
from ..modular.train import write_json
from .network import PlaceMemory,HIDDEN
from .task import make_places,sample_sequence,sample_headings


def recording(model,detector,seed,size=21,length=67):
    places=make_places(seed,size);rng=random.Random(seed+1)
    ids,truth=sample_sequence(places,length,rng,balanced=True)
    headings=sample_headings(length,rng)
    gates=(detector(mx.array([places['oriented_detector_readings'][point][heading] for point,heading in zip(ids,headings)]))>.5).tolist()
    h=mx.zeros((1,HIDDEN));c=mx.zeros_like(h);frames=[];score=0
    for i,(point,label) in enumerate(zip(ids,truth)):
        heading=headings[i]
        readings=places['oriented_readings'][point][heading]
        x=mx.array([readings])
        before=float(mx.sqrt(mx.mean(h*h)))
        logit,h,c=model.step(x,mx.array([gates[i]]),h,c)
        p=float(mx.sigmoid(logit)[0]);answer=p>.5;correct=answer==bool(label)
        score+=1 if correct else -1
        frames.append(dict(index=i+1,x=places['points'][point][0],y=places['points'][point][1],
                           readings=readings,heading=heading,answer=answer,probability=p,
                           truth=bool(label),correct=correct,reward=1 if correct else -1,
                           score=score,stored=gates[i],memory_before=before,
                           memory_after=float(mx.sqrt(mx.mean(h*h)))))
    return dict(maze=places['maze'].payload(),frames=frames,points=places['points'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,default=Path('games/maze/models/place_memory_random_heading_v3'));p.add_argument('--port',type=int,default=8773)
    args=p.parse_args();mx.set_default_device(mx.gpu)
    model=PlaceMemory();model.load_weights(str(args.model/'memory.safetensors'))
    detector=JunctionDetector();detector.load_weights(str(args.model/'detector.safetensors'))
    mx.eval(model.parameters(),detector.parameters())
    state=dict(report=json.loads((args.model/'report.json').read_text()));counter=0
    def new():
        nonlocal counter
        counter+=1;state['recording']=recording(model,detector,97000000+counter)
        return state
    new()
    class Handler(BaseHTTPRequestHandler):
        def reply(self,data,kind='application/json'):
            if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path=='/':self.reply(Path(__file__).with_name('index.html').read_bytes(),'text/html; charset=utf-8')
            elif self.path=='/api/state':self.reply(state)
            else:self.send_error(404)
        def do_POST(self):
            if self.path=='/api/next':self.reply(new())
            else:self.send_error(404)
        def log_message(self,*_):pass
    print(f'Stedshukommelse: http://127.0.0.1:{args.port}',flush=True)
    HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
