import json
import math
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from games.car import app
from games.car.crash_spawns import PoseTrail,CrashSpawnBank
from games.car.scenarios import Scenario
from games.car.track import Track
from collections import deque
from ai.network import NeuralNetwork
from games.car.rotating import train_generation


class CrashSpawnTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'points.sqlite'
        self.bank=CrashSpawnBank(self.path)
        self.track=Track([(0,0),(1000,0),(1000,1000),(0,1000)],name='test').set_backend('rust')
        self.pose=dict(x=100.,y=0.,z=0.,heading=0.,speed_ratio=1.)
        self.crash=dict(x=240.,y=32.,z=0.)

    def tearDown(self):
        self.bank.db.close();self.directory.cleanup()

    def add(self,direction=1):return self.bank.add_crash(self.track,direction,self.pose,self.crash,31)

    def test_ten_lengths_are_actual_travel_with_interpolated_pose(self):
        trail=PoseTrail(140.)
        for x in (0.,50.,100.,150.,200.):
            trail.append(dict(x=x,y=0.,z=0.,heading=0.,speed=3.,speed_factor=1.))
        pose=trail.before_crash();self.assertAlmostEqual(pose['x'],60.)
        self.assertEqual(pose['speed_ratio'],1.)
        short=PoseTrail(140.);short.append(dict(x=0.,y=0.,heading=0.));short.append(dict(x=50.,y=0.,heading=0.))
        self.assertIsNone(short.before_crash())

    def test_twenty_completed_tests_and_inflight_reservations_never_overbook(self):
        point=self.add();rng=random.Random(42)
        reservations=[self.bank.reserve(self.track,1,rng,lambda p:True) for _ in range(20)]
        self.assertTrue(all(reservations));self.assertIsNone(self.bank.reserve(self.track,1,rng,lambda p:True))
        for index,reservation in enumerate(reservations,1):
            result=self.bank.complete(reservation['token']);self.assertEqual(result['tests'],index)
            self.assertIsNone(self.bank.complete(reservation['token']))
        self.assertIsNone(self.bank.reserve(self.track,1,rng,lambda p:True))
        self.assertEqual(self.add(),point)  # A repeat crash must not reset the limit.
        self.assertIsNone(self.bank.reserve(self.track,1,rng,lambda p:True))

    def test_track_direction_geometry_and_occupied_places_are_separate(self):
        self.add();rng=random.Random(2)
        self.assertIsNone(self.bank.reserve(self.track,-1,rng,lambda p:True))
        self.assertIsNone(self.bank.reserve(self.track,1,rng,lambda p:False))
        other=Track(self.track.points,half_width=40.,name='other')
        self.assertIsNone(self.bank.reserve(other,1,rng,lambda p:True))
        changed=Track(self.track.points,half_width=40.,name='test')
        self.assertIsNone(self.bank.reserve(changed,1,rng,lambda p:True))
        self.assertEqual(self.bank.db.execute('SELECT count(*) FROM reservations').fetchone()[0],0)

    def test_persistence_and_recovery_keep_completed_tests(self):
        self.add();rng=random.Random(3)
        first=self.bank.reserve(self.track,1,rng,lambda p:True);self.bank.complete(first['token'])
        self.bank.reserve(self.track,1,rng,lambda p:True)
        self.bank.db.close();self.bank=CrashSpawnBank(self.path);self.bank.register_track(self.track)
        self.assertEqual(self.bank.markers('test')[0]['tests'],1)
        self.assertEqual(self.bank.markers('test')[0]['pending'],1)
        self.bank.recover_pending()
        self.assertEqual(self.bank.markers('test')[0]['tests'],1)
        self.assertEqual(self.bank.markers('test')[0]['pending'],0)

    def test_saved_starts_have_original_pose_and_group_direction(self):
        self.add()
        with patch.object(app,'TRACK',self.track):
            scenario=Scenario(3,1,no_cones=True,crash_spawns=self.bank,crash_spawn_share=1.)
            cars=scenario.initial()
            # Other active cars can block a point, so place them well away from it.
            for index,car in enumerate(cars[1:],1):car.update(x=700.,y=index*40.)
            scenario.prepare_drive(cars,0)
            self.assertEqual(cars[0]['spawn_source'],'saved')
            self.assertEqual((cars[0]['x'],cars[0]['y'],cars[0]['heading']),(100.,0.,0.))
            self.assertEqual({c['direction'] for c in cars},{1})
            result=scenario.finish_drive(cars[0]);self.assertEqual(result['tests'],1)
            self.assertIsNone(scenario.finish_drive(cars[0]))

    def test_ten_percent_selection_and_evaluation_stays_random(self):
        self.add()
        with patch.object(app,'TRACK',self.track):
            scenario=Scenario(44,1,no_cones=True,crash_spawns=self.bank,crash_spawn_share=.1)
            chosen=0
            for _ in range(1000):
                car=dict(x=500.,y=0.,z=0.,heading=0.,direction=1,speed_factor=1.,crashed=False,_new_drive=True)
                scenario.prepare_drive([car],0)
                if car['spawn_source']=='saved':
                    chosen+=1
                    # Release these sampling probes rather than spending the 20-test quota.
                    with self.bank.db:self.bank.db.execute('DELETE FROM reservations')
            self.assertTrue(70<=chosen<=130,chosen)
            plain=Scenario(44,1,no_cones=True)
            before=plain.evaluation_starts(2)
            self.assertEqual(before,Scenario(44,1,no_cones=True).evaluation_starts(2))
            self.assertEqual(self.bank.markers('test')[0]['tests'],0)

    def test_actual_trainer_discovers_an_approach_then_counts_its_saved_start(self):
        car=dict(self.pose,direction=1,speed_factor=1.,speed=3.,travel=0.,crashed=False,restarts=0)
        car.pop('speed_ratio')
        def step(cars,weights,controls,events=None):
            for i,c in enumerate(cars):
                if c['crashed']:continue
                c['x']+=10.;c['travel']+=10.;c['_test_steps']=c.get('_test_steps',0)+1
                if c['_test_steps']==20:
                    c['y']=32.;c['crashed']=True;events.append((i,'wall',None))
        with patch.object(app,'TRACK',self.track),patch.object(app,'PROGRESS_ONLY_REWARD',0.),patch.object(app,'DIRECTIONAL_COLLISIONS',False),patch.object(app,'step',side_effect=step),patch('games.car.rotating.features',return_value=[1.]):
            scenario=Scenario(33,1,no_cones=True,crash_spawns=self.bank,crash_spawn_share=1.)
            result=train_generation([NeuralNetwork([1,1])],40,2,[car],[deque()],4,
                                    scenario=scenario,pass_only=True,continue_survivors=True)
        first,second=result['records']
        self.assertIsNotNone(first['new_crash_point_id'])
        self.assertEqual(second['spawn_source'],'saved')
        self.assertEqual(second['practice_point_id'],first['new_crash_point_id'])
        self.assertEqual(second['practice_test']['tests'],1)
        self.assertEqual(self.bank.db.execute('SELECT count(*) FROM reservations').fetchone()[0],0)
