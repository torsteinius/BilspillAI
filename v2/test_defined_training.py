import math
import unittest
from unittest.mock import patch
from ai.laser_vision import LaserVisionNetwork
from games.car import app,hybrid
from games.car.track import Track
from games.car.training_tracks import DEFINED_TRACKS
from games.car.multi_track import TrackPool
from games.car.laser_radar import walls,ray_angles,scan
from games.car.native_evaluation import evaluate
from ai.rust_backend import native_module


class DefinedTrainingTests(unittest.TestCase):
    def test_open_geometry_has_no_return_wall(self):
        for name in DEFINED_TRACKS[:2]:
            track=Track.generate(name)
            self.assertFalse(track.closed)
            self.assertEqual(len(track.segments),len(track.points)-1)
            self.assertEqual(len(walls(track)),2*(len(track.points)-1))
            self.assertNotEqual(track.pose(0),track.pose(track.perimeter))
            self.assertFalse(track.path.endswith('Z'))
        self.assertTrue(all(p[1]==0 for p in Track.generate('bridge_straight').points))

    def test_both_laser_layers_tilt_with_body_and_native_pitch_matches(self):
        track=Track([(0,0,0),(100,0,0),(200,0,30),(300,0,30)],closed=False).set_backend('rust')
        car=dict(track.pose(98),speed=3.,speed_factor=1.,direction=1,crashed=False)
        pitch=track.pitch(car['x'],car['y'],car['z'],car['heading'])
        self.assertGreater(pitch,0) # nose reaches ramp before centre
        self.assertAlmostEqual(pitch,track.native.pitch(car['x'],car['y'],car['z'],car['heading']))
        radar=native_module().LaserRadar(walls(track),ray_angles())
        expected=radar.scan(car['x'],car['y'],car['z'],car['heading'],pitch,3.,540.,[])
        with patch.object(app,'TRACK',track),patch.object(app,'RADAR_RANGE',540.),patch.object(app,'ROAD_ONLY',True):
            actual=scan(app,car,[car],0.)
        for layer in (0,1):
            for i in range(layer*61,(layer+1)*61):self.assertAlmostEqual(actual[i]['distance'],expected[i][0])
        reverse=track.pitch(car['x'],car['y'],car['z'],math.pi)
        self.assertAlmostEqual(reverse,-pitch)

    def test_finish_reward_python_and_rust_in_both_directions(self):
        pool=TrackPool(DEFINED_TRACKS,20,1,standard_starts=True)
        actor=LaserVisionNetwork().set_backend('rust') # zero outputs: straight
        for direction in (1,-1):
            with pool.use('bridge_straight'),patch.object(app,'ROAD_ONLY',True),patch.object(app,'RADAR_MODE','laser2'),patch.object(hybrid,'NATIVE_EVALUATION',False),patch.object(app,'PROGRESS_ONLY_REWARD',.05):
                track=app.TRACK
                pose=track.pose(track.perimeter-2 if direction==1 else 2)
                pose['heading']+=math.pi if direction<0 else 0
                cars=[dict(pose,direction=direction,speed_factor=1.,speed=3.,travel=0.,crashed=False) for _ in range(5)]
                py=hybrid.evaluate_candidate(actor,actor,20,initial_cars=cars,pass_only=True)
                rust=evaluate(actor,actor,20,initial_cars=cars,pass_only=True)
                for expected,actual in zip(py['roles'],rust['roles']):
                    self.assertFalse(actual['collision'])
                    self.assertEqual(actual['steps'],1)
                    self.assertAlmostEqual(actual['reward'],50.1)
                    self.assertAlmostEqual(actual['reward'],expected['reward'])

    def test_standard_starts_repeat_and_stay_at_entrance(self):
        pool=TrackPool(DEFINED_TRACKS,20,1,standard_starts=True)
        with pool.use('tight_turns'),patch.object(app,'ROAD_ONLY',True):
            scenario=pool.training_scenario('tight_turns',1,5)
            cars=scenario.initial()
            self.assertEqual(cars,scenario.initial())
            for i,car in enumerate(cars):
                along=app.TRACK.progress(car['x'],car['y'],car['z'])
                self.assertAlmostEqual(along if car['direction']>0 else app.PERIMETER-along,30.+i*30.)

    def test_training_finish_is_rewarded_and_restarted(self):
        from collections import deque
        from games.car.rotating import train_generation
        pool=TrackPool(DEFINED_TRACKS,20,1,standard_starts=True)
        actor=LaserVisionNetwork().set_backend('rust')
        with pool.use('bridge_straight'),patch.object(app,'ROAD_ONLY',True),patch.object(app,'RADAR_MODE','laser2'),patch.object(app,'PROGRESS_ONLY_REWARD',.05):
            scenario=pool.training_scenario('bridge_straight',1,5)
            cars=scenario.initial()
            for car in cars:
                car.update(app.TRACK.pose(app.PERIMETER-1 if car['direction']>0 else 1))
                if car['direction']<0:car['heading']+=math.pi
            result=train_generation([actor],20,1,cars,[deque() for _ in cars],3,scenario=scenario,pass_only=True)
            self.assertEqual(result['attempts'],[1])
            self.assertEqual(result['records'][0]['end_reason'],'finish')
            self.assertFalse(result['records'][0]['collision'])
            self.assertGreaterEqual(result['records'][0]['reward'],50.)
            self.assertFalse(any(car.get('finished',False) for car in cars))
