import math
import unittest
from unittest.mock import patch
from games.car import app,hybrid
from games.car.progress_guard import insufficient_progress,PROGRESS_WINDOW
from games.car.multi_track import TrackPool
from games.car.native_evaluation import evaluate
from ai.laser_vision import LaserVisionNetwork


class ProgressGuardTests(unittest.TestCase):
    def test_threshold_is_relative_to_standard_speed_inclusive(self):
        for factor in (.8,1.,1.2):
            car={'speed_factor':factor}
            for _ in range(100):self.assertFalse(insufficient_progress(car,.3*3*factor))
            car={'speed_factor':factor}
            for _ in range(PROGRESS_WINDOW-1):self.assertFalse(insufficient_progress(car,.29*3*factor))
            self.assertTrue(insufficient_progress(car,.29*3*factor))

    def test_net_progress_rejects_backtracking_and_old_progress_cannot_bank_time(self):
        car={}
        for _ in range(30):self.assertFalse(insufficient_progress(car,3.))
        for _ in range(30):failed=insufficient_progress(car,0.)
        self.assertTrue(failed)
        car={}
        for i in range(30):failed=insufficient_progress(car,3. if i%2 else -3.)
        self.assertTrue(failed)

    def test_circle_is_stopped_and_penalized_identically_in_both_engines(self):
        pool=TrackPool(['bridge_straight'],200,1)
        actor=LaserVisionNetwork().set_backend('rust')
        # Zero hidden activations; output biases alone give fixed steering/braking.
        actor.weights[-1]=math.atanh(-.999)
        actor.weights[-34]=math.atanh(-.999)
        self.assertLess(actor.forward([0.]*366)[0],-.99)
        with pool.use('bridge_straight'),patch.object(app,'ROAD_ONLY',True),patch.object(app,'RADAR_MODE','laser2'),patch.object(app,'MAX_BRAKE',.7),patch.object(app,'STEERING_BOOST',.5),patch.object(app,'PROGRESS_ONLY_REWARD',.05),patch.object(app,'SPEED_WEIGHTED_PROGRESS',True),patch.object(hybrid,'NATIVE_EVALUATION',False):
            cars=[dict(app.TRACK.pose(600),direction=1,speed_factor=1.,travel=0.,crashed=False) for _ in range(5)]
            expected=hybrid.evaluate_candidate(actor,actor,200,initial_cars=cars,pass_only=True)
            actual=evaluate(actor,actor,200,initial_cars=cars,pass_only=True)
            for a,b in zip(expected['roles'],actual['roles']):
                self.assertEqual(a['steps'],30)
                self.assertEqual(a['steps'],b['steps'])
                self.assertTrue(a['collision']);self.assertTrue(b['collision'])
                self.assertLess(a['reward'],-49.)
                self.assertAlmostEqual(a['reward'],b['reward'],places=7)
            car=cars[0];events=[]
            for _ in range(30):app.step([car],[],controls=[(-.999,.999,0.)],events=events)
            self.assertEqual(car['end_reason'],'low_progress')
            self.assertIn((0,'low_progress',None),events)

    def test_maximum_braking_straight_ahead_meets_thirty_percent(self):
        pool=TrackPool(['bridge_straight'],200,1)
        with pool.use('bridge_straight'),patch.object(app,'ROAD_ONLY',True),patch.object(app,'MAX_BRAKE',.7):
            for direction in (1,-1):
                car=dict(app.TRACK.pose(600),direction=direction,speed_factor=.8,travel=0.,crashed=False)
                if direction<0:car['heading']+=math.pi
                for _ in range(100):app.step([car],[],controls=[(0.,1.,0.)])
                self.assertFalse(car['crashed'])
