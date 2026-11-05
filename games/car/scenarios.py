"""Seeded generation layouts and collision-free random convoy starts."""
import math
import random
from . import app


def separation(a,b):
    return math.dist((a['x'],a['y'],a.get('z',0.)),(b['x'],b['y'],b.get('z',0.)))


class Scenario:
    def __init__(self,seed,generation,world=app):
        self.world=world
        self.seed=seed
        self.generation=generation
        self.direction=1 if generation%2 else -1
        self.rng=random.Random(seed+generation*100003+1)
        layout_rng=random.Random(seed+generation*100003)
        self.cones=[]
        for i in range(layout_rng.randint(4,8)):
            for _ in range(10000):
                p=self.world.TRACK.pose(layout_rng.random()*self.world.TRACK.perimeter,
                                 layout_rng.uniform(-self.world.TRACK.half_width+22,self.world.TRACK.half_width-22))
                cone=dict(x=p['x'],y=p['y'],z=p['z'],radius=6.,kind='cone',crashed=False,target_id=f'cone:{generation}:{i}')
                if self.world.TRACK.clearance(p['x'],p['y'],p['z'])>=20 and all(separation(cone,c)>24 for c in self.cones):
                    self.cones.append(cone);break
            else:raise RuntimeError('Could not place separated cones')
        self.world.TRACK.cones=self.cones

    def spawn(self,index,cars,rng):
        for _ in range(10000):
            pose=self.world.TRACK.pose(rng.random()*self.world.TRACK.perimeter,
                                rng.uniform(-self.world.TRACK.half_width+self.world.CAR_RADIUS+4,
                                            self.world.TRACK.half_width-self.world.CAR_RADIUS-4))
            if self.world.TRACK.clearance(pose['x'],pose['y'],pose['z'])<self.world.CAR_RADIUS+2:continue
            if any(separation(pose,c)<self.world.CAR_RADIUS+c['radius']+8 for c in self.cones):continue
            if any(not c['crashed'] and separation(pose,c)<2*self.world.CAR_RADIUS+12 for c in cars):continue
            pose['heading']+=math.pi if self.direction<0 else 0.
            return dict(pose,direction=self.direction,speed_factor=self.world.SPEED_FACTORS[index],
                        travel=0.,crashed=False,restarts=0,target_id=f'car:{index}')
        raise RuntimeError('Could not find free random start')

    def initial(self,rng=None):
        rng=self.rng if rng is None else rng
        cars=[]
        for i in range(5):cars.append(self.spawn(i,cars,rng))
        return cars

    def restart_car(self,cars,index):
        car=cars[index];start=self.spawn(index,[c for i,c in enumerate(cars) if i!=index],self.rng)
        start['restarts']=car['restarts']+1
        car.clear();car.update(start)

    def restart_crashed(self,cars):
        for i,car in enumerate(cars):
            if car['crashed']:self.restart_car(cars,i)

    def evaluation_starts(self,count,holdout=False):
        rng=random.Random(self.seed+self.generation*100003+(3 if holdout else 2))
        return [self.initial(rng) for _ in range(count)]

    def payload(self):
        # Screen y points down: positive signed area is clockwise on the map.
        pts=self.world.TRACK.points
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1]))
        return dict(generation=self.generation,seed=self.seed,direction=self.direction,
                    direction_label='clockwise' if area*self.direction>0 else 'counterclockwise',cones=self.cones)
