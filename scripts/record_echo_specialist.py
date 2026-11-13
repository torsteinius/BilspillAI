"""Record actual saved-policy actions, then render with the media environment.

.venv-training/bin/python scripts/record_echo_specialist.py simulate
.venv-media/bin/python scripts/record_echo_specialist.py render
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT/'docs/media/turn-echo-drive.json'
VIDEO = ROOT/'docs/media/turn-echo-drive.mp4'
MODEL = ROOT/'games/car/models/turn_specialists/preserved_2026-11-11/turn_echo.json'


def simulate():
    from ai.network import NeuralNetwork
    from games.car.train_turn_specialists import use_track, spawn
    from games.car.track import Track
    from games.car.turn_sensors import inputs, scan
    from games.car import app
    track = Track.generate('tight_turns')
    use_track(track)
    net = NeuralNetwork.load(MODEL).set_backend('rust')
    car = spawn(track, 30., 1)
    frames = []
    for step in range(6500):
        if step % 3 == 0:
            frames.append(dict(step=step, car=car.copy(), rays=scan(track, car, 'turn_echo')))
        out = net.forward(inputs(track, car, 'turn_echo'))
        app.step([car], [], controls=[(out[0], (out[1]+1)/2, 0.)])
        if car['crashed'] or car.get('finished'):
            frames.append(dict(step=step+1, car=car.copy(), rays=scan(track, car, 'turn_echo')))
            break
    result = dict(model=str(MODEL.relative_to(ROOT)), sha256=hashlib.sha256(MODEL.read_bytes()).hexdigest(),
                  track=track.name, points=track.points, half_width=track.half_width,
                  finished=bool(car.get('finished')), crashed=car['crashed'], steps=step+1,
                  playback='3 simulation steps per frame, 30 fps', frames=frames)
    DATA.write_text(json.dumps(result))
    print(json.dumps({k:v for k,v in result.items() if k not in ('points','frames')}), flush=True)


def render():
    from PIL import Image, ImageDraw, ImageFont
    import imageio_ffmpeg
    import subprocess
    data=json.loads(DATA.read_text())
    font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
    font=ImageFont.truetype(font_path, 22)
    small=ImageFont.truetype(font_path, 17)
    writer=subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error',
        '-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','30',
        '-i','-','-an','-vcodec','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(VIDEO)],stdin=subprocess.PIPE)
    points=data['points']
    xmin=min(p[0] for p in points); xmax=max(p[0] for p in points)
    ymin=min(p[1] for p in points); ymax=max(p[1] for p in points)
    mini_scale=min(260/(xmax-xmin),190/(ymax-ymin))
    def mini(p):return (980+(p[0]-xmin)*mini_scale,150+(p[1]-ymin)*mini_scale)
    edges=[[], []]
    for i,p in enumerate(points):
        a=points[max(0,i-1)]; b=points[min(len(points)-1,i+1)]
        dx=b[0]-a[0]; dy=b[1]-a[1]; length=math.hypot(dx,dy)
        for side,sign in enumerate((-1,1)):
            edges[side].append((p[0]-sign*dy/length*data['half_width'],p[1]+sign*dx/length*data['half_width']))
    preview=None
    try:
        for i,frame in enumerate(data['frames']):
            car=frame['car']; im=Image.new('RGB',(1280,720),'#101824');d=ImageDraw.Draw(im)
            scale=1.35
            def xy(p):return (620+(p[0]-car['x'])*scale,400+(p[1]-car['y'])*scale)
            left,right=([xy(p) for p in edge] for edge in edges)
            d.polygon(left+list(reversed(right)),fill='#344354')
            d.line(left,fill='#d8e0e9',width=2)
            d.line(right,fill='#d8e0e9',width=2)
            for ray in frame['rays']:
                path=[xy(p) for p in ray['points']]
                for j in range(len(path)-1):
                    d.line(path[j:j+2],fill=(25, max(70,210-j*28), max(90,240-j*25)),width=2)
                for echo in ray['echoes']:
                    x,y=xy(echo['point']);d.ellipse((x-3,y-3,x+3,y+3),fill='#ffe290')
            co=math.cos(car['heading']);si=math.sin(car['heading'])
            body=[xy((car['x']+a*co-b*si,car['y']+a*si+b*co)) for a,b in ((12,0),(-9,-7),(-9,7))]
            d.polygon(body,fill='#ffbd58',outline='white')
            d.rectangle((0,0,1280,100),fill='#101824')
            d.text((28,20),'EKKO-BILEN  |  Faktisk kjøring med lagrede vekter',font=font,fill='white')
            d.text((28,57),'Ti stråler · opptil fem refleksjoner · flat svingbane · uten trafikk',font=small,fill='#a9c0d7')
            d.rectangle((950,118,1260,380),fill='#182535',outline='#557087')
            d.text((969,126),'Hele banen',font=small,fill='white')
            d.line([mini(p) for p in points],fill='#8396aa',width=3)
            x,y=mini((car['x'],car['y']));d.ellipse((x-5,y-5,x+5,y+5),fill='#ffbd58')
            d.rectangle((0,650,1280,720),fill='#101824')
            status='Mål nådd uten krasj' if car.get('finished') else 'Krasj' if car['crashed'] else 'Kjører'
            d.text((28,668),f"{status}  |  Steg {frame['step']}  |  3 steg/bilde, 30 bilder/s",font=font,fill='white')
            writer.stdin.write(im.tobytes())
            if i==len(data['frames'])//3:preview=im.copy()
        for _ in range(60):writer.stdin.write(im.tobytes())
    finally:
        writer.stdin.close()
        code=writer.wait()
    if code:raise RuntimeError(f'ffmpeg exited {code}')
    preview.save(VIDEO.with_suffix('.png'))
    print(VIDEO)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('simulate','render'))
    args=parser.parse_args()
    simulate() if args.action=='simulate' else render()
