"""Read-only view of actual rotating-training frames, independent of the trainer."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

from . import app


class FrameWriter:
    def __init__(self,path,architecture,target,fan_degrees,interval=.25,crash_spawns=None):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.architecture=list(architecture);self.target=target;self.fan=fan_degrees
        self.interval=interval;self.last=0.;self.payload=None
        self.crash_spawns=crash_spawns

    def _write(self):
        temporary=None
        try:
            with tempfile.NamedTemporaryFile('w',dir=self.path.parent,delete=False) as stream:
                temporary=stream.name;json.dump(self.payload,stream,allow_nan=False)
            os.replace(temporary,self.path);temporary=None
        finally:
            if temporary is not None:Path(temporary).unlink(missing_ok=True)

    def __call__(self,frame):
        now=time.monotonic()
        if self.payload and now-self.last<self.interval and frame['track']==self.payload['track'] and frame['generation']==self.payload['generation']:return
        self.last=now
        cars=[{key:value for key,value in car.items() if not key.startswith('_')}
              for car in frame['cars']]
        self.payload=dict(frame,road_only=app.ROAD_ONLY,cars=cars,timestamp=time.time(),live_training=True,
            architecture=self.architecture,generations=self.target,radar_mode='laser2',
            laser_vertical_fan_degrees=self.fan,training=True,phase='training',
            training_cars=len(cars),background_cars=0,traffic='convoy',speed=1,fast=False,
            best_score=None,current_score=None,simulation_steps=frame['steps_limit'])
        if self.crash_spawns:self.payload['practice_points']=self.crash_spawns.markers(frame['track'])
        self._write()

    def phase(self,phase,generation=None,**updates):
        if self.payload is None:return
        self.payload=dict(self.payload,phase=phase,training=phase!='complete',timestamp=time.time(),**updates)
        if generation is not None:self.payload['generation']=generation
        if self.crash_spawns:self.payload['practice_points']=self.crash_spawns.markers(self.payload['track'])
        self._write()


class TrainingView:
    def __init__(self,path):
        self.path=Path(path);self.stamp=None;self.raw=None;self.prepared=None
        self.lock=threading.Lock();self.tracks={}
        app.configure_traffic('convoy');app.configure_radar(3.)
        app.ROAD_ONLY=True;app.RADAR_MODE='laser2'

    def read(self):
        try:stamp=self.path.stat().st_mtime_ns
        except FileNotFoundError:return None
        if stamp!=self.stamp:
            frame=json.loads(self.path.read_text());name=frame['track']
            if name not in app.Track.NAMES:raise ValueError('Unknown live track')
            if name not in self.tracks:
                track=app.Track.generate(name).set_backend('rust');track.cones=[]
                self.tracks[name]=track
            track=self.tracks[name]
            app.TRACK=track;app.PERIMETER=track.perimeter
            app.LASER_VERTICAL_FAN_DEGREES=frame['laser_vertical_fan_degrees']
            app.ROAD_ONLY=frame.get('road_only',True)
            cars=frame['cars']
            prepared=dict(frame,angles=[],reason='',validation=[],
                candidate=0,population=len(frame['completed']),
                scenario_direction=frame['scenario']['direction_label'],
                cars=[dict(car,waiting=frame['owners'][index] is None,sensors=[],
                           radar=app.radar(car,cars) if frame['owners'][index] is not None else
                               dict(detected=False,shape='laser2',rays=[],range=app.RADAR_RANGE,distance=app.RADAR_RANGE),
                           pitch=track.pitch(car['x'],car['y'],car.get('z',0.),car['heading']),
                           lap=round(100*max(0,car['travel'])/track.perimeter,1)) for index,car in enumerate(cars)])
            self.raw=frame;self.prepared=prepared;self.stamp=stamp
        return dict(self.prepared,frame_age_seconds=max(0.,time.time()-self.prepared['timestamp']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8768)
    args=parser.parse_args();view=TrainingView(args.frames)
    class Handler(app.Handler):
        def do_POST(self):self.send_error(405,'The training view is read-only')
        def do_GET(self):
            with view.lock:
                frame=view.read()
                if frame is None:
                    body=b'<meta charset="utf-8"><meta http-equiv="refresh" content="2"><h1>Venter p\xc3\xa5 f\xc3\xb8rste treningsbilde \xe2\x80\xa6</h1>'
                    self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
                elif self.path=='/api/state':
                    body=json.dumps(frame).encode();self.send_response(200)
                    self.send_header('Content-Type','application/json')
                else:
                    super().do_GET();return
                self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)))
                self.end_headers();self.wfile.write(body)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Direkte fra trening: http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()


if __name__=='__main__':main()
