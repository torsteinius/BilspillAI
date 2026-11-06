import unittest
from collections import deque
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car import app
from games.car.scenarios import Scenario,separation
from games.car.rotating import train_generation
from games.car.hybrid import evaluate_candidate

class BackgroundTrafficTests(unittest.TestCase):
    def test_only_five_cars_learn_and_background_keeps_moving(self):
        actors=[NeuralNetwork([1,1]) for _ in range(10)]
        background=[NeuralNetwork([1,1]) for _ in range(15)]
        original=[n.weights[:] for n in background]
        cars=[dict(travel=0.,crashed=False) for _ in range(20)]
        histories=[deque() for _ in cars]
        def step(cars,weights,controls):
            self.assertEqual(len(controls),20)
            for c in cars:
                if not c['crashed']:c['travel']+=1.
        with patch('games.car.rotating.app.restart_crashed'),patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda n:n):
            result=train_generation(actors,2,3,cars,histories,12,background_models=background,pass_only=True)
        self.assertEqual(result['attempts'],[3]*10)
        self.assertTrue(all(r['car']<5 and r['reward']==0 for r in result['records']))
        self.assertTrue(all(c['travel']==result['ticks'] for c in cars[5:]))
        self.assertTrue(all(not h for h in histories[5:]))
        self.assertEqual([n.weights for n in background],original)

    def test_twenty_random_starts_and_respawns_clear_other_cars(self):
        old=app.TRACK
        try:
            app.configure_track('training');s=Scenario(20261115,1,car_count=20,no_cones=True);cars=s.initial()
            self.assertEqual(len(cars),20);self.assertFalse(s.cones)
            for i,a in enumerate(cars):
                for b in cars[i+1:]:self.assertGreaterEqual(separation(a,b),2*app.CAR_RADIUS+12)
            cars[19]['crashed']=True;s.restart_crashed(cars)
            self.assertFalse(cars[19]['crashed']);self.assertEqual(cars[19]['restarts'],1)
        finally:app.configure_track(old.name)

    def test_eval_no_progress_reward_and_five_roles_only(self):
        n=NeuralNetwork([1,1]);cars=[dict(travel=0.,crashed=False) for _ in range(20)]
        def step(cars,weights,controls):
            for c in cars:c['travel']+=3.
        with patch('games.car.hybrid.features',return_value=[1.]),patch.object(app,'step',side_effect=step):
            result=evaluate_candidate(n,n,4,initial_cars=cars,background_models=[n]*15,pass_only=True)
        self.assertEqual(len(result['roles']),5);self.assertEqual(result['score'],0);self.assertEqual(result['distance'],60)

    def test_only_background_slows_at_start_and_respawn(self):
        old=app.TRACK
        try:
            app.configure_track('training');s=Scenario(42,2,car_count=20,no_cones=True,background_speed_scale=.85);cars=s.initial()
            for i,c in enumerate(cars):self.assertAlmostEqual(c['speed_factor'],app.SPEED_FACTORS[i%5]*(.85 if i>=5 else 1.))
            cars[7]['crashed']=True;s.restart_crashed(cars)
            self.assertAlmostEqual(cars[7]['speed_factor'],.85)
            self.assertEqual(s.payload()['background_speed_scale'],.85)
        finally:app.configure_track(old.name)
