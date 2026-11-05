import math
import random
import unittest
from collections import deque
from ai.network import NeuralNetwork
from games.car import app
from games.car.temporal import Experience, distribute_collision, forward_gradient, Adam


def entry(t,target=None):
    return Experience(t,[0.]*11,0.,target,[0.],0.,[0.])

class TemporalTests(unittest.TestCase):
    def test_credit_is_conserved_and_peaks_before_collision(self):
        history=deque(entry(t) for t in range(100))
        allocation=distribute_collision(history)
        self.assertAlmostEqual(sum(r['penalty'] for r in allocation),50.)
        self.assertAlmostEqual(history[-1].reward,-5.)
        for lag,share in [(3,.3),(6,.3),(12,.15),(24,.15)]:
            self.assertAlmostEqual(sum(r['penalty'] for r in allocation if abs(r['lag']-lag)<=1),50*share)
        self.assertTrue(all(e.reward==0 for e in list(history)[:-26]))

    def test_short_history_and_unseen_target_preserve_penalty(self):
        for size in (1,2,10):
            history=deque(entry(t) for t in range(size))
            distribute_collision(history)
            self.assertAlmostEqual(sum(e.reward for e in history),-50.)
        history=deque(entry(t,'other') for t in range(100))
        distribute_collision(history,'collision-car')
        self.assertEqual(history[-1].reward,-50.)
        self.assertEqual(sum(e.reward for e in list(history)[:-1]),0.)

    def test_object_identity_and_latest_encounter(self):
        history=deque(entry(t,'A' if t<20 or 40<=t<=46 else 'B') for t in range(50))
        allocation=distribute_collision(history,'A')
        self.assertTrue(all(40<=r['tick']<=46 for r in allocation))
        self.assertAlmostEqual(sum(r['penalty'] for r in allocation),50.)

    def test_immediate_control(self):
        history=deque(entry(t) for t in range(100))
        allocation=distribute_collision(history,mode='immediate')
        self.assertEqual(allocation,[dict(tick=99,lag=0,penalty=50.)])

    def test_gradient_matches_finite_difference_and_policy(self):
        rng=random.Random(22)
        network=NeuralNetwork([3,4,2,1]);network.weights=[rng.uniform(-.3,.3) for _ in network.weights]
        inputs=[.3,-.7,.1]
        value,gradient=forward_gradient(network,inputs)
        self.assertAlmostEqual(math.tanh(value),network.forward(inputs)[0])
        for i in range(len(network.weights)):
            old=network.weights[i]; eps=1e-6
            network.weights[i]=old+eps; plus=forward_gradient(network,inputs)[0]
            network.weights[i]=old-eps; minus=forward_gradient(network,inputs)[0]
            network.weights[i]=old
            self.assertAlmostEqual(gradient[i],(plus-minus)/(2*eps),places=7)

    def test_negative_credit_reduces_sample_probability(self):
        network=NeuralNetwork([1,1]);network.weights=[0.,0.]
        mean,gradient=forward_gradient(network,[1.])
        sample=.2;sigma=.25
        Adam(2).apply(network.weights,[-1*(sample-mean)/sigma**2*g for g in gradient])
        new_mean=forward_gradient(network,[1.])[0]
        self.assertGreater(abs(sample-new_mean),abs(sample-mean))

    def test_explicit_controls_preserve_old_physics(self):
        app.configure_track();app.configure_traffic('convoy')
        oldmode=app.RADAR_MODE;app.RADAR_MODE='legacy'
        try:
            network=NeuralNetwork([9,8,8,1]);oldnet=app.network;app.network=network
            a=app.initial();b=[dict(c) for c in a]
            weights=[0.]*network.weight_count
            expected=app.step(a,weights)
            events=[];actual=app.step(b,weights,controls=[0.]*5,events=events)
            self.assertEqual(expected,actual);self.assertEqual(a,b)
        finally:
            app.network=oldnet;app.RADAR_MODE=oldmode;app.configure_traffic('opposite')

    def test_collision_events_identify_cone_for_correct_car(self):
        app.configure_track()
        try:
            app.TRACK.cones=[dict(x=450.,y=130.,z=0.,radius=6.,kind='cone',crashed=False,target_id='cone:0')]
            car=dict(x=436.,y=130.,z=0.,heading=0.,direction=1,travel=0.,crashed=False)
            events=[]
            app.step([car],[],controls=[0.],events=events)
            self.assertTrue(car['crashed'])
            self.assertIn((0,'cone','cone:0'),events)
        finally:
            app.configure_track()

    def test_uniform50_penalizes_all_recent_actions_equally(self):
        history=deque(entry(t,'different-object') for t in range(100))
        allocation=distribute_collision(history,'collision-object',mode='uniform50')
        self.assertEqual(len(allocation),50)
        self.assertTrue(all(r['penalty']==1. for r in allocation))
        self.assertTrue(all(e.reward==0. for e in list(history)[:50]))
        self.assertTrue(all(e.reward==-1. for e in list(history)[50:]))
        short=deque(entry(t) for t in range(10))
        distribute_collision(short,mode='uniform50')
        self.assertTrue(all(e.reward==-5. for e in short))
