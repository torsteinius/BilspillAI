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

def boundaries(track):
    boundaries=[[],[]];points=track.points
    for i,p in enumerate(points):
        before=points[i-1] if i or track.closed else (2*p[0]-points[1][0],2*p[1]-points[1][1],p[2])
        after=points[(i+1)%len(points)] if i<len(points)-1 or track.closed else (2*p[0]-points[-2][0],2*p[1]-points[-2][1],p[2])
        dx,dy=p[0]-before[0],p[1]-before[1];d=math.hypot(dx,dy);n1=(-dy/d,dx/d)
        dx,dy=after[0]-p[0],after[1]-p[1];d=math.hypot(dx,dy);n2=(-dy/d,dx/d)
        den=1+n1[0]*n2[0]+n1[1]*n2[1]
        if den<.1:raise ValueError('Track corner too sharp')
        for side,sign in zip(boundaries,(-1,1)):
            side.append((p[0]+sign*track.half_width*(n1[0]+n2[0])/den,p[1]+sign*track.half_width*(n1[1]+n2[1])/den,p[2]))
    return boundaries

def walls(track):
    return [(*a,*b) for side in boundaries(track) for a,b in zip(side,side[1:]+(side[:1] if track.closed else []))]

def road_triangles(track):
    left,right=boundaries(track)
    return [triangle for i in range(len(left) if track.closed else len(left)-1)
            for triangle in ((left[i],left[(i+1)%len(left)],right[(i+1)%len(left)]),
                             (left[i],right[(i+1)%len(left)],right[i]))]

def scan(world,car,cars,vertical_fan_degrees=None):
    global _CACHE
    if _CACHE is None or _CACHE[0] is not world.TRACK:
        radar=native_module().LaserRadar(walls(world.TRACK),ray_angles())
        _CACHE=(world.TRACK,radar,False)
    fan=getattr(world,'LASER_VERTICAL_FAN_DEGREES',0.) if vertical_fan_degrees is None else vertical_fan_degrees
    if fan and not _CACHE[2]:
        _CACHE[1].set_ground(road_triangles(world.TRACK))
        _CACHE=(*_CACHE[:2],True)
    objects=[]
    for c in world.others(car,cars)+world.TRACK.cones:
        if c.get('crashed',False):continue
        cone=c.get('kind')=='cone';speed=0. if cone else c.get('speed',3*c.get('speed_factor',1.))
        objects.append((c['x'],c['y'],c.get('z',0.),c.get('radius',world.CAR_RADIUS),speed*math.cos(c.get('heading',0.)),speed*math.sin(c.get('heading',0.)),1 if cone else 2))
    pitch=world.TRACK.pitch(car['x'],car['y'],car.get('z',0.),car['heading'])
    args=(car['x'],car['y'],car.get('z',0.),car['heading'],pitch,car.get('speed',3*car.get('speed_factor',1.)),world.RADAR_RANGE,objects)
    rows=_CACHE[1].scan_fan(*args,math.radians(fan)) if fan else _CACHE[1].scan(*args)
    return [dict(distance=r[0],closing_speed=r[1],forward=r[2],lateral=r[3],kind=('wall','cone','car','road')[r[4]] if r[4]>=0 else None,detected=r[4]>=0,echo_strength=r[6],angle=ray_angles()[i%61],height=(.5,3.)[i//61],layer=i//61) for i,r in enumerate(rows)]

def inputs(world,car,cars,vertical_fan_degrees=None):
    return [v for r in scan(world,car,cars,vertical_fan_degrees) for v in (r['distance']/world.RADAR_RANGE,max(-1.,min(1.,r['closing_speed']/10.8)),r['echo_strength'])]
