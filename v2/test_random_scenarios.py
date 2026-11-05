import copy
import math
import unittest
from collections import deque
from games.car import app
from games.car.scenarios import Scenario, separation
from games.car.hybrid import evaluate_suite
from games.car.rotating import train_generation
from ai.network import NeuralNetwork


class RandomScenarioTests(unittest.TestCase):
    def setUp(self):
        self.saved={k:getattr(app,k) for k in ('TRACK','clearance','progress','PERIMETER','PATH','HALF_WIDTH','SIMULATION_STEPS','cars','TRAFFIC','RADAR_MODE','RADAR_RANGE','RADAR_RADIUS','RADAR_OFFSET','RADAR_SCALE')}
        self.status=app.status.copy()
        app.configure_track('training');app.configure_traffic('convoy')
        app.configure_radar(3);app.RADAR_MODE='cone4relative';app.TRACK.set_backend('rust')

    def tearDown(self):
        for k,v in self.saved.items():setattr(app,k,v)
        app.status.clear();app.status.update(self.status)

    def test_seeded_layouts_alternate_direction_and_cover_counts(self):
        counts=set()
        for gen in range(1,31):
            a=Scenario(456,gen);payload=copy.deepcopy(a.payload());starts=a.evaluation_starts(2)
            b=Scenario(456,gen)
            self.assertEqual(payload,b.payload());self.assertEqual(starts,b.evaluation_starts(2))
            counts.add(len(b.cones));self.assertEqual(b.direction,1 if gen%2 else -1)
            for c in b.cones:
                self.assertGreaterEqual(app.clearance(c['x'],c['y'],c['z']),20)
                for other in b.cones:
                    if other is not c:self.assertGreater(separation(c,other),24)
            cars=b.initial();self.assertTrue(all(c['direction']==b.direction for c in cars))
            app.step(cars,[],controls=[(0.,0.)]*5)
            self.assertTrue(all(c['travel']>0 for c in cars))
        self.assertEqual(counts,{4,5,6,7,8})

    def test_random_restarts_are_safe_and_leave_others_alone(self):
        scenario=Scenario(12,4);cars=scenario.initial()
        for _ in range(30):
            before=copy.deepcopy(cars);scenario.restart_car(cars,0)
            self.assertNotEqual((cars[0]['x'],cars[0]['y']),(before[0]['x'],before[0]['y']))
            self.assertEqual(cars[1:],before[1:])
            self.assertEqual(cars[0]['direction'],-1)
            self.assertTrue(all(separation(cars[0],c)>=26 for c in cars[1:]))
            self.assertTrue(all(separation(cars[0],c)>=21 for c in scenario.cones))

    def test_evaluation_reuses_starts_without_mutating_them(self):
        scenario=Scenario(44,2);starts=scenario.evaluation_starts(2);before=copy.deepcopy(starts)
        n=NeuralNetwork([23,8,2]).set_backend('rust')
        a=evaluate_suite(n,n,20,[0,0],starts=starts)
        scenario.initial() # unrelated training RNG draws must not affect tests
        b=evaluate_suite(n,n,20,[0,0],starts=starts)
        self.assertEqual(a,b);self.assertEqual(starts,before)

    def test_timeout_randomizes_start_and_clears_old_location_history(self):
        scenario=Scenario(2,1);cars=scenario.initial();histories=[deque() for c in cars]
        actors=[NeuralNetwork([23,8,2]).set_backend('rust') for _ in range(10)]
        result=train_generation(actors,1,2,cars,histories,7,history_stride=3,scenario=scenario)
        self.assertEqual(result['attempts'],[2]*10)
        self.assertTrue(all(not h for h in histories))
        starts=[(r['start_pose']['x'],r['start_pose']['y']) for r in result['records']]
        self.assertEqual(len(set(starts)),20)
