"""Configurable forward zones: nearest road edge or obstacle surface in each zone.

Road edges are a mitered offset of the sampled centreline, with segment heights. Geometry
is cached; exact closest points on these segments/discs are calculated in Rust.
"""
import math
from functools import lru_cache
from ai.rust_backend import native_module

_CACHE=None

@lru_cache(maxsize=4)
def sector_edges(mode):
    if mode=='sectors15':return [-math.pi/2+i*math.pi/15 for i in range(16)]
    if mode in ('sectors30wide','sectors30echo'):
        old=sector_edges('sectors30');a=old[16]-old[15];b=4*(old[-1]-old[-2])
        low,high=.01,100.
        for _ in range(60):
            power=(low+high)/2
            if sum(a+(b-a)*(i/14)**power for i in range(15))>math.radians(110):low=power
            else:high=power
        positive=[0.]
        for i in range(15):positive.append(positive[-1]+a+(b-a)*(i/14)**((low+high)/2))
        return [-v for v in reversed(positive[1:])]+positive
    if mode!='sectors30':raise ValueError('Unknown sector radar mode')
    # Density decreases linearly from 2 at the nose to 1 at +/-90 degrees.
    # Equal probability intervals of its integral give smoothly varying widths.
    positive=[math.pi/2*(2-math.sqrt(4-3*i/15)) for i in range(16)]
    return [-v for v in reversed(positive[1:])]+positive


def road_edges(track):
    from .laser_radar import boundaries
    return [(a[0],a[1],b[0],b[1],(a[2]+b[2])/2)
            for side in boundaries(track)
            for a,b in zip(side,side[1:]+(side[:1] if track.closed else []))]


def scan(world,car,cars,mode=None):
    global _CACHE
    mode=mode or world.RADAR_MODE
    edges=sector_edges(mode)
    if _CACHE is None or _CACHE[0] is not world.TRACK or _CACHE[2]!=mode:
        _CACHE=(world.TRACK,native_module().SectorRadar(road_edges(world.TRACK),edges),mode)
    objects=[]
    for c in world.others(car,cars)+world.TRACK.cones:
        if c.get('crashed',False):continue
        cone=c.get('kind')=='cone';speed=0. if cone else c.get('speed',3*c.get('speed_factor',1.))
        objects.append((c['x'],c['y'],c.get('z',0.),c.get('radius',world.CAR_RADIUS),speed*math.cos(c.get('heading',0.)),speed*math.sin(c.get('heading',0.)),1 if cone else 2))
    reader=_CACHE[1].scan_echo if mode=='sectors30echo' else _CACHE[1].scan
    rows=reader(car['x'],car['y'],car.get('z',0.),car['heading'],car.get('speed',3*car.get('speed_factor',1.)),world.RADAR_RANGE,objects)
    return [dict(distance=r[0],closing_speed=r[1],forward=r[2],lateral=r[3],kind=('wall','cone','car')[r[4]] if r[4]>=0 else None,detected=r[4]>=0,echo_strength=r[6] if len(r)>6 else None,angle=(edges[i]+edges[i+1])/2,angle_low=edges[i],angle_high=edges[i+1]) for i,r in enumerate(rows)]

def inputs(world,car,cars,mode=None):
    mode=mode or world.RADAR_MODE
    return [v for r in scan(world,car,cars,mode) for v in (r['distance']/world.RADAR_RANGE,max(-1.,min(1.,r['closing_speed']/10.8)))+((r['echo_strength'],) if mode=='sectors30echo' else ())]
