import copy
import math
import unittest
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car import app
from games.car.hybrid import add_throttle_output, Learner
from games.car.overtaking import OvertakeTracker


class ThrottleTests(unittest.TestCase):
    def test_expansion_preserves_all_existing_weights_and_outputs(self):
        old=NeuralNetwork([23,8,8,8,8,2],seed=7)
        old.weights=[math.sin(i)*.2 for i in range(old.weight_count)]
        new=add_throttle_output(old,22)
        self.assertEqual(new.weights[:old.weight_count],old.weights)
        self.assertEqual(len(new.weights)-len(old.weights),9)
        self.assertNotEqual(new.weights[-9:],[0.]*9)
        for backend in ('python','rust'):
            old.set_backend(backend);new.set_backend(backend)
            for value in (-1.,0.,1.):
                self.assertEqual(new.forward([value]*23)[:2],old.forward([value]*23))
        learner=Learner(new,12);action=learner.choose(0,[.1]*23)
        self.assertEqual(len(action),3)
        self.assertEqual(len(learner.history[-1].latent),3)
        self.assertEqual(learner.history[-1].action,action)

    def test_throttle_and_brake_speed(self):
        self.assertEqual(app.decode_outputs([0.,-1.,-1.]),(0.,0.,0.))
        self.assertEqual(app.decode_outputs([0.,-1.,1.]),(0.,0.,1.))
        for brake,gas,expected in [(0,0,3),(0,1,4.5),(1,1,2.25)]:
            car=dict(x=0.,y=0.,z=0.,heading=0.,direction=1,travel=0.,crashed=False)
            with patch.object(app,'progress',side_effect=lambda x,y,z=0:x),patch.object(app,'clearance',return_value=100),patch.object(app.TRACK,'locate',return_value=(0,0,0)),patch.object(app.TRACK,'cones',[]),patch.object(app,'NATIVE_CAR_KERNELS',False):
                app.step([car],[],controls=[(0.,brake,gas)])
            self.assertEqual(car['speed'],expected)


class OvertakingTests(unittest.TestCase):
    def cars(self,direction=1):
        return [dict(x=0.,y=0.,direction=direction,travel=0.,crashed=False,restarts=0),dict(x=40.*direction,y=0.,direction=direction,travel=0.,crashed=False,restarts=0)]

    def drive(self,cars,tracker,direction=1):
        total=0
        for _ in range(70):
            for i,c in enumerate(cars):
                d=2. if i==0 else 1.
                c['x']+=d*direction;c['travel']+=d
            total+=tracker.update(cars)[0]
        return total

    def test_pass_both_directions_once_and_no_spawn_or_wreck_bonus(self):
        with patch.object(app,'progress',side_effect=lambda x,y,z=0:x),patch.object(app,'same_level',return_value=True),patch.object(app,'PERIMETER',1000):
            for direction in (1,-1):
                cars=self.cars(direction);tracker=OvertakeTracker();tracker.update(cars,advance=False)
                self.assertEqual(self.drive(cars,tracker,direction),1)
                self.assertEqual(self.drive(cars,tracker,direction),0)
            cars=self.cars();tracker=OvertakeTracker();tracker.update(cars,advance=False)
            cars[0].update(x=70.,restarts=1)
            self.assertEqual(self.drive(cars,tracker),0)
            cars=self.cars();tracker=OvertakeTracker();tracker.update(cars,advance=False)
            cars[1]['crashed']=True
            self.assertEqual(self.drive(cars,tracker),0)
            cars=self.cars();cars[1]['direction']=-1;tracker=OvertakeTracker()
            self.assertEqual(self.drive(cars,tracker),0)

    def test_crossing_lap_boundary_is_a_real_pass(self):
        with patch.object(app,'progress',side_effect=lambda x,y,z=0:x%1000),patch.object(app,'same_level',return_value=True),patch.object(app,'PERIMETER',1000):
            cars=self.cars()
            for c in cars:c['x']+=980
            tracker=OvertakeTracker();tracker.update(cars,advance=False)
            self.assertEqual(self.drive(cars,tracker),1)
