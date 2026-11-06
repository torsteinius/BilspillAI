import math
import random
import unittest
from ai.network import NeuralNetwork
from games.car import app
from games.car.hybrid import Learner, driving_reward
from games.car.temporal import forward_gradient

class BrakingTests(unittest.TestCase):
    def setUp(self):
        app.configure_track()
        self.old_mode=app.RADAR_MODE
        app.RADAR_MODE='cone4relative'

    def tearDown(self):
        app.RADAR_MODE=self.old_mode
        app.configure_track()

    def car(self):
        return dict(x=400.,y=130.,z=0.,heading=0.,direction=1,travel=0.,crashed=False,speed_factor=1.)

    def test_brake_limits_motion_and_progress_reward(self):
        distances=[]
        for brake,expected in ((0.,3.),(.5,2.25),(1.,1.5)):
            car=self.car()
            app.step([car],[],controls=[(0.,brake)])
            self.assertAlmostEqual(car['x']-400.,expected)
            self.assertAlmostEqual(car['speed'],expected)
            self.assertFalse(car['crashed'])
            distances.append(car['travel'])
        self.assertGreater(driving_reward(distances[0],False),driving_reward(distances[2],False))

    def test_radar_reports_actual_braked_speed(self):
        ego=self.car();target=dict(ego,x=450.)
        app.step([target],[],controls=[(0.,1.)])
        reading=app.radar(ego,[target])
        self.assertAlmostEqual(reading['speed'],1.5)
        self.assertAlmostEqual(reading['closing_speed'],1.5)
        self.assertAlmostEqual(reading['relative_speed'],-1.5)
        ego['speed']=1.5
        self.assertAlmostEqual(app.radar(ego,[target])['closing_speed'],0.)

    def test_seventy_percent_braking_keeps_actual_speed_for_radar(self):
        old=app.MAX_BRAKE
        try:
            app.MAX_BRAKE=.7
            for brake,expected in ((0.,3.),(.5,1.95),(1.,.9)):
                car=self.car()
                app.step([car],[],controls=[(0.,brake)])
                self.assertAlmostEqual(car['speed'],expected)
                self.assertAlmostEqual(car['x']-400.,expected)
            ego=self.car();target=dict(ego,x=450.)
            app.step([target],[],controls=[(0.,1.)])
            self.assertAlmostEqual(app.radar(ego,[target])['speed'],.9)
            self.assertAlmostEqual(app.radar(ego,[target])['relative_speed'],-2.1)
            car=self.car();app.step([car],[],controls=[(0.,0.,1.)])
            self.assertAlmostEqual(car['speed'],4.5)
        finally:
            app.MAX_BRAKE=old

    def test_two_outputs_have_correct_gradients(self):
        rng=random.Random(9);net=NeuralNetwork([2,3,2]);net.weights=[rng.uniform(-.3,.3) for _ in net.weights]
        x=[.2,-.4]
        for output in (0,1):
            value,gradient=forward_gradient(net,x,output)
            self.assertAlmostEqual(math.tanh(value),net.forward(x)[output])
            for i in range(net.weight_count):
                old=net.weights[i];eps=1e-6
                net.weights[i]=old+eps;a=forward_gradient(net,x,output)[0]
                net.weights[i]=old-eps;b=forward_gradient(net,x,output)[0]
                net.weights[i]=old
                self.assertAlmostEqual(gradient[i],(a-b)/(2*eps),places=7)

    def test_history_keeps_brake_and_penalizes_both_heads_after_update(self):
        learner=Learner(NeuralNetwork([1,2]),19)
        action=learner.choose(0,[1.]);learner.observe(1.,False)
        self.assertEqual(len(action),2)
        self.assertTrue(0<=action[1]<=1)
        self.assertEqual(learner.history[-1].action,action)
        self.assertEqual(len(learner.history[-1].latent),2)
        learner.finish(False);learner.begin(preserve_history=True)
        learner.choose(1,[1.]);learner.observe(0.,True)
        result=learner.finish(True)
        self.assertAlmostEqual(result['reward'],-50.)
        self.assertTrue(any(abs(g)>0 for g in learner.gradient[:2]))
        self.assertTrue(any(abs(g)>0 for g in learner.gradient[2:]))
        self.assertFalse(learner.history)

    def test_output_mapping_and_legacy_compatibility(self):
        self.assertEqual(app.decode_outputs([.2]),.2)
        self.assertEqual(app.decode_outputs([.2,-1.]),(.2,0.))
        self.assertEqual(app.decode_outputs([.2,1.]),(.2,1.))
        car=self.car();app.step([car],[],controls=[0.])
        self.assertEqual(car['speed'],3.)

    def test_equal_speeds_and_stationary_cone_are_ego_relative(self):
        ego=self.car();target=dict(ego,x=450.)
        reading=app.radar(ego,[target])
        self.assertEqual(reading['relative_speed'],0.)
        self.assertEqual(reading['closing_speed'],0.)
        self.assertEqual(app.observations(ego,[target])[9:11],[0.,0.])
        target.update(kind='cone',radius=6.)
        reading=app.radar(ego,[target])
        self.assertEqual(reading['relative_speed'],-3.)
        self.assertEqual(reading['closing_speed'],3.)
        obs=app.observations(ego,[target])
        self.assertAlmostEqual(obs[9],-3/7.2)
        self.assertAlmostEqual(obs[10],3/7.2)

    def test_relative_velocity_respects_heading(self):
        ego=self.car();ego['heading']=math.pi/2
        target=dict(ego,y=180.,speed=1.5)
        reading=app.radar(ego,[target])
        self.assertAlmostEqual(reading['relative_speed'],-1.5)
        self.assertAlmostEqual(reading['closing_speed'],1.5)

    def test_four_hidden_layers_gradient_and_history_update(self):
        rng=random.Random(7)
        network=NeuralNetwork([23,8,8,8,8,2])
        network.weights=[rng.uniform(-.3,.3) for _ in network.weights]
        inputs=[rng.uniform(-1,1) for _ in range(23)]
        for output in (0,1):
            value,gradient=forward_gradient(network,inputs,output)
            self.assertAlmostEqual(math.tanh(value),network.forward(inputs)[output])
            for i in range(0,network.weight_count,13):
                old=network.weights[i];eps=1e-6
                network.weights[i]=old+eps;a=forward_gradient(network,inputs,output)[0]
                network.weights[i]=old-eps;b=forward_gradient(network,inputs,output)[0]
                network.weights[i]=old
                self.assertAlmostEqual(gradient[i],(a-b)/(2*eps),places=7)
        learner=Learner(network,7)
        old_weights=network.weights[:]
        learner.choose(0,inputs);learner.observe(2.,False);learner.finish(False)
        learner.begin(preserve_history=True)
        learner.choose(1,inputs);learner.observe(0.,True);learner.finish(True)
        self.assertNotEqual(old_weights,network.weights)
        self.assertTrue(all(math.isfinite(v) for v in network.weights))
        self.assertEqual(learner.baseline.architecture,(23,8,8,8,8,1))
