"""Configurable forward zones: nearest road edge or obstacle surface in each zone.

Flat-track road edges are a mitered offset of the sampled centreline. Geometry
is cached; exact closest points on these segments/discs are calculated in Rust.
"""
import math
from functools import lru_cache
from ai.rust_backend import native_module

_CACHE=None

@lru_cache(maxsize=3)
def sector_edges(mode):
    if mode=='sectors15':return [-math.pi/2+i*math.pi/15 for i in range(16)]
    if mode=='sectors30wide':
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
    if max(p[2] for p in track.points)-min(p[2] for p in track.points)>1e-6:
        raise ValueError('Sector radar experiment currently requires a flat track')
    boundaries=[[],[]];points=track.points
    for i,p in enumerate(points):
        before=points[i-1];after=points[(i+1)%len(points)]
        dx,dy=p[0]-before[0],p[1]-before[1];d=math.hypot(dx,dy);n1=(-dy/d,dx/d)
        dx,dy=after[0]-p[0],after[1]-p[1];d=math.hypot(dx,dy);n2=(-dy/d,dx/d)
        denominator=1+n1[0]*n2[0]+n1[1]*n2[1]
        if denominator<.1:raise ValueError('Track corner too sharp for sector boundary')
        nx,ny=(n1[0]+n2[0])/denominator,(n1[1]+n2[1])/denominator
        for side,sign in zip(boundaries,(-1,1)):side.append((p[0]+sign*track.half_width*nx,p[1]+sign*track.half_width*ny,p[2]))
    return [(a[0],a[1],b[0],b[1],(a[2]+b[2])/2) for side in boundaries for a,b in zip(side,side[1:]+side[:1])]

def scan(world,car,cars):
    global _CACHE
    edges=sector_edges(world.RADAR_MODE)
    if _CACHE is None or _CACHE[0] is not world.TRACK or _CACHE[2]!=world.RADAR_MODE:
        _CACHE=(world.TRACK,native_module().SectorRadar(road_edges(world.TRACK),edges),world.RADAR_MODE)
    objects=[]
    for c in world.others(car,cars)+world.TRACK.cones:
        if c.get('crashed',False):continue
        cone=c.get('kind')=='cone';speed=0. if cone else c.get('speed',3*c.get('speed_factor',1.))
        objects.append((c['x'],c['y'],c.get('z',0.),c.get('radius',world.CAR_RADIUS),speed*math.cos(c.get('heading',0.)),speed*math.sin(c.get('heading',0.)),1 if cone else 2))
    rows=_CACHE[1].scan(car['x'],car['y'],car.get('z',0.),car['heading'],car.get('speed',3*car.get('speed_factor',1.)),world.RADAR_RANGE,objects)
    return [dict(distance=d,closing_speed=v,forward=x,lateral=y,kind=('wall','cone','car')[k] if k>=0 else None,detected=k>=0,angle=(edges[i]+edges[i+1])/2,angle_low=edges[i],angle_high=edges[i+1]) for i,(d,v,x,y,k,_) in enumerate(rows)]

def inputs(world,car,cars):
    return [v for r in scan(world,car,cars) for v in (r['distance']/world.RADAR_RANGE,max(-1.,min(1.,r['closing_speed']/10.8)))]
