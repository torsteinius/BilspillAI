"""Seeded generation layouts and collision-free random convoy starts."""
import math
import random
from . import app


def separation(a,b):
    return math.dist((a['x'],a['y'],a.get('z',0.)),(b['x'],b['y'],b.get('z',0.)))


class Scenario:
    def __init__(self,seed,generation,world=app,car_count=5,no_cones=False,background_speed_scale=1.,training_count=5,crash_spawns=None,crash_spawn_share=.1,standard_starts=False):
        if not 5<=car_count<=25 or not 1<=training_count<=10 or training_count>car_count:raise ValueError("Invalid car/learner count")
        self.standard_starts=standard_starts or not world.TRACK.closed
        self.training_count=training_count
        if not math.isfinite(background_speed_scale) or not 0<background_speed_scale<=1:raise ValueError('Background speed scale must be in (0,1]')
        self.background_speed_scale=background_speed_scale
        self.car_count=car_count
        self.world=world
        if not math.isfinite(crash_spawn_share) or not 0<=crash_spawn_share<=1:raise ValueError('Invalid saved-spawn share')
        self.crash_spawns=crash_spawns;self.crash_spawn_share=crash_spawn_share
        self.practice_rng=random.Random(seed+generation*100003+8731)
        self.track_name=world.TRACK.name
        points=world.TRACK.points
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
        self.seed=seed
        self.generation=generation
        self.direction=1 if generation%2 else -1
        self.direction_label='clockwise' if area*self.direction>0 else 'counterclockwise'
        self.rng=random.Random(seed+generation*100003+1)
        layout_rng=random.Random(seed+generation*100003)
        self.cones=[]
        for i in range(0 if no_cones else layout_rng.randint(4,8)):
            for _ in range(10000):
                p=self.world.TRACK.pose(layout_rng.random()*self.world.TRACK.perimeter,
                                 layout_rng.uniform(-self.world.TRACK.half_width+22,self.world.TRACK.half_width-22))
                cone=dict(x=p['x'],y=p['y'],z=p['z'],radius=6.,kind='cone',crashed=False,target_id=f'cone:{generation}:{i}')
                if self.world.TRACK.clearance(p['x'],p['y'],p['z'])>=20 and all(separation(cone,c)>24 for c in self.cones):
                    self.cones.append(cone);break
            else:raise RuntimeError('Could not place separated cones')
        self.world.TRACK.cones=self.cones

    def spawn(self,index,cars,rng):
        if any(not car['crashed'] and car.get('direction',self.direction)!=self.direction for car in cars):
            raise ValueError('Cannot spawn against the direction of active cars; start a new scenario first')
        if self.standard_starts:
            # A fixed grid at the entrance, never at a saved crash or random bend.
            distance=30.+index*30.
            along=distance if self.direction>0 else self.world.TRACK.perimeter-distance
            pose=self.world.TRACK.pose(along)
            pose['heading']+=math.pi if self.direction<0 else 0.
            if not self.world.ROAD_ONLY and any(not c['crashed'] and separation(pose,c)<26 for c in cars):
                return dict(pose,direction=self.direction,speed_factor=1.,travel=0.,crashed=True,restarts=0,target_id=f'car:{index}')
            return dict(pose,direction=self.direction,speed_factor=self.world.SPEED_FACTORS[index%len(self.world.SPEED_FACTORS)],travel=0.,crashed=False,restarts=0,target_id=f'car:{index}')
        for _ in range(10000):
            pose=self.world.TRACK.pose(rng.random()*self.world.TRACK.perimeter,
                                rng.uniform(-self.world.TRACK.half_width+self.world.CAR_RADIUS+4,
                                            self.world.TRACK.half_width-self.world.CAR_RADIUS-4))
            if self.world.TRACK.clearance(pose['x'],pose['y'],pose['z'])<self.world.CAR_RADIUS+2:continue
            if any(separation(pose,c)<self.world.CAR_RADIUS+c['radius']+8 for c in self.cones):continue
            if any(not c['crashed'] and separation(pose,c)<2*self.world.CAR_RADIUS+12 for c in cars):continue
            pose['heading']+=math.pi if self.direction<0 else 0.
            return dict(pose,direction=self.direction,speed_factor=self.world.SPEED_FACTORS[index%len(self.world.SPEED_FACTORS)]*(self.background_speed_scale if index>=self.training_count else 1.),
                        travel=0.,crashed=False,restarts=0,target_id=f'car:{index}')
        raise RuntimeError('Could not find free random start')

    def initial(self,rng=None):
        rng=self.rng if rng is None else rng
        cars=[]
        for i in range(self.car_count):
            car=self.spawn(i,cars,rng)
            if self.crash_spawns:car['_new_drive']=True
            cars.append(car)
        return cars

    def restart_car(self,cars,index):
        car=cars[index];start=self.spawn(index,[c for i,c in enumerate(cars) if i!=index],self.rng)
        start['restarts']=car['restarts']+1
        if self.crash_spawns:start['_new_drive']=True
        car.clear();car.update(start)

    def prepare_drive(self,cars,index):
        car=cars[index]
        if not self.crash_spawns or not car.pop('_new_drive',False):return
        car['spawn_source']='random'
        if self.practice_rng.random()>=self.crash_spawn_share:return
        def safe(pose):
            if self.world.TRACK.clearance(pose['x'],pose['y'],pose['z'])<self.world.CAR_RADIUS+2:return False
            return not any(i!=index and not other['crashed'] and separation(pose,other)<2*self.world.CAR_RADIUS+12 for i,other in enumerate(cars))
        saved=self.crash_spawns.reserve(self.world.TRACK,self.direction,self.practice_rng,safe)
        if saved is None:return
        pose=dict(saved['pose']);ratio=pose.pop('speed_ratio',1.)
        pose['speed']=3*car['speed_factor']*max(1-self.world.MAX_BRAKE,min(1.5,ratio))
        car.update(pose,spawn_source='saved',practice_point_id=saved['id'],_practice_reservation=saved['token'])

    def finish_drive(self,car):
        token=car.pop('_practice_reservation',None)
        return self.crash_spawns.complete(token) if self.crash_spawns and token else None

    def restart_crashed(self,cars):
        for i,car in enumerate(cars):
            if car['crashed']:self.restart_car(cars,i)

    def evaluation_starts(self,count,holdout=False):
        rng=random.Random(self.seed+self.generation*100003+(3 if holdout else 2))
        return [self.initial(rng) for _ in range(count)]

    def payload(self):
        # Screen y points down: positive signed area is clockwise on the map.
        return dict(start_mode='standard' if self.standard_starts else 'random',track=self.track_name,generation=self.generation,seed=self.seed,direction=self.direction,car_count=self.car_count,training_count=self.training_count,background_speed_scale=self.background_speed_scale,
                    direction_label=self.direction_label,cones=self.cones)
