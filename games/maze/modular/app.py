"""View a completed modular experiment separately from the legacy maze app."""
import argparse
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import mlx.core as mx
from ..generator import generate
from .networks import Perception, Memory, Decision
from .train import rollout


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',type=Path,default=Path('games/maze/models/modular_lstm_v2'))
    p.add_argument('--port',type=int,default=8771)
    args=p.parse_args()
    mx.set_default_device(mx.gpu)
    perception,memory,decision=Perception(),Memory(),Decision()
    for name,model in [('perception',perception),('memory',memory),('decision',decision)]:
        model.load_weights(str(args.model/(name+'.safetensors')))
    mx.eval(perception.parameters(),memory.parameters(),decision.parameters())
    state={'report':json.loads((args.model/'report.json').read_text()),'recording':None}
    counter=0
    def next_recording(size=15,zero=False):
        nonlocal counter
        if size not in (5,9,15):raise ValueError('Size must be 5, 9 or 15')
        counter+=1
        maze=generate(size,size,seed=95000000+counter)
        world,frames=rollout(perception,memory,decision,maze,zero,True)
        state['recording']=dict(id=counter,maze=maze.payload(),frames=frames,zero_memory=zero)
        return state
    next_recording()
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
                self.reply(next_recording(int(body.get('size',15)),bool(body.get('zero',False))))
            except (ValueError,TypeError):self.send_error(400)
        def log_message(self,*_):pass
    print(f'Modulært LSTM-forsøk: http://127.0.0.1:{args.port}',flush=True)
    HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()


if __name__=='__main__':main()
