"""Two-height straight ray observations, computed in Rust."""
import math
from functools import lru_cache
from ai.rust_backend import native_module
from .sector_radar import sector_edges
_CACHE=None

@lru_cache(maxsize=1)
def ray_angles():
    edges=sector_edges('sectors30wide')
    return [a for lo,hi in zip(edges,edges[1:]) for a in (lo,(lo+hi)/2)]+[edges[-1]]

def walls(track):
    boundaries=[[],[]];points=track.points
    for i,p in enumerate(points):
        before=points[i-1];after=points[(i+1)%len(points)]
        dx,dy=p[0]-before[0],p[1]-before[1];d=math.hypot(dx,dy);n1=(-dy/d,dx/d)
        dx,dy=after[0]-p[0],after[1]-p[1];d=math.hypot(dx,dy);n2=(-dy/d,dx/d)
        den=1+n1[0]*n2[0]+n1[1]*n2[1]
        if den<.1:raise ValueError('Track corner too sharp')
        for side,sign in zip(boundaries,(-1,1)):
            side.append((p[0]+sign*track.half_width*(n1[0]+n2[0])/den,p[1]+sign*track.half_width*(n1[1]+n2[1])/den,p[2]))
    return [(*a,*b) for side in boundaries for a,b in zip(side,side[1:]+side[:1])]

def scan(world,car,cars):
    global _CACHE
    if _CACHE is None or _CACHE[0] is not world.TRACK:
        _CACHE=(world.TRACK,native_module().LaserRadar(walls(world.TRACK),ray_angles()))
    objects=[]
    for c in world.others(car,cars)+world.TRACK.cones:
        if c.get('crashed',False):continue
        cone=c.get('kind')=='cone';speed=0. if cone else c.get('speed',3*c.get('speed_factor',1.))
        objects.append((c['x'],c['y'],c.get('z',0.),c.get('radius',world.CAR_RADIUS),speed*math.cos(c.get('heading',0.)),speed*math.sin(c.get('heading',0.)),1 if cone else 2))
    pitch=world.TRACK.pitch(car['x'],car['y'],car.get('z',0.),car['heading'])
    rows=_CACHE[1].scan(car['x'],car['y'],car.get('z',0.),car['heading'],pitch,car.get('speed',3*car.get('speed_factor',1.)),world.RADAR_RANGE,objects)
    return [dict(distance=r[0],closing_speed=r[1],forward=r[2],lateral=r[3],kind=('wall','cone','car')[r[4]] if r[4]>=0 else None,detected=r[4]>=0,echo_strength=r[6],angle=ray_angles()[i%61],height=(.5,3.)[i//61],layer=i//61) for i,r in enumerate(rows)]

def inputs(world,car,cars):
    return [v for r in scan(world,car,cars) for v in (r['distance']/world.RADAR_RANGE,max(-1.,min(1.,r['closing_speed']/10.8)),r['echo_strength'])]
