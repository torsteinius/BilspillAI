import unittest,math,tempfile
from unittest.mock import patch
from pathlib import Path
from ai.laser_vision import LaserVisionNetwork,ARCHITECTURE
from ai.local_vision import LocalVisionNetwork,ECHO
from ai.network import NeuralNetwork
from ai.rust_backend import native_module
from games.car import app,hybrid
from games.car.laser_radar import ray_angles,scan,walls
from games.car.track import Track
from games.car.native_evaluation import evaluate

class LaserTests(unittest.TestCase):
    def test_layers_gap_and_echo(self):
        radar=native_module().LaserRadar([(40.,-20.,0.,40.,20.,0.)],[0.,.5])
        objects=[(20.,0.,0.,4.,1.,0.,2)]
        rows=radar.scan(0.,0.,0.,0.,0.,3.,100.,objects)
        self.assertEqual(rows[0][4],0);self.assertAlmostEqual(rows[0][0],40.)
        self.assertEqual(rows[2][4],2);self.assertAlmostEqual(rows[2][0],16.)
        self.assertAlmostEqual(rows[2][1],2.);self.assertAlmostEqual(rows[2][6],1.)
        self.assertEqual(rows[3][4],-1) # a discrete ray misses the car
        self.assertEqual(rows[3][6],0.)
    def test_ramp_and_overpass(self):
        radar=native_module().LaserRadar([(40.,-20.,4.,40.,20.,4.)],[0.])
        rows=radar.scan(0.,0.,0.,0.,math.atan(.1),3.,100.,[])
        self.assertEqual(rows[0][4],0);self.assertAlmostEqual(rows[0][0],math.hypot(40,4))
        radar=native_module().LaserRadar([(40.,-20.,40.,40.,20.,40.)],[0.])
        rows=radar.scan(0.,0.,0.,0.,0.,3.,100.,[(20.,0.,40.,4.,0.,0.,2)])
        self.assertTrue(all(r[4]==-1 for r in rows))
    def test_training_lasers_follow_real_ramp_in_both_directions(self):
        track=Track.generate('figure_eight').set_backend('rust')
        segment=track.segments[170]
        pose=track.pose(segment[5]+segment[8]/2)
        radar=native_module().LaserRadar(walls(track),ray_angles())
        actor=LaserVisionNetwork()
        for reverse in (False,True):
            car=dict(pose,heading=pose['heading']+(math.pi if reverse else 0.),
                     crashed=False,speed=3.,speed_factor=1.)
            pitch=track.pitch(car['x'],car['y'],car['z'],car['heading'])
            self.assertGreater(abs(pitch),.15)
            with patch.object(app,'TRACK',track),patch.object(app,'RADAR_RANGE',540.),patch.object(app,'ROAD_ONLY',True):
                rays=scan(app,car,[car])
                inputs=app.model_observations(actor,car,[car])
            tilted=radar.scan(car['x'],car['y'],car['z'],car['heading'],pitch,3.,540.,[])
            horizontal=radar.scan(car['x'],car['y'],car['z'],car['heading'],0.,3.,540.,[])
            self.assertGreater(sum(r['kind']=='wall' for r in rays[:61]),20)
            self.assertLess(sum(r[4]==0 for r in horizontal[:61]),5)
            for index,(ray,expected) in enumerate(zip(rays,tilted)):
                self.assertAlmostEqual(ray['distance'],expected[0])
                self.assertAlmostEqual(inputs[index*3],expected[0]/540.)
    def test_locality_and_roundtrip(self):
        n=LaserVisionNetwork(seed=8);n.randomize();self.assertEqual(len(ray_angles()),61)
        row=n.links[0][4*30]
        self.assertEqual(set(i//3 for i in row),{29,30,31,90,91,92})
        self.assertNotIn(60*3,n.links[0][0])
        x=[.2]*366;py=n.forward(x);n.set_backend('rust');rust=n.forward(x)
        for a,b in zip(py,rust):self.assertAlmostEqual(a,b,places=10)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.json';n.save(p);loaded=NeuralNetwork.load(p)
            self.assertEqual(loaded.weights,n.weights);self.assertEqual(loaded.links,n.links)
    def test_mixed_native_matches_python(self):
        saved=(app.TRACK,app.RADAR_MODE,app.STEERING_BOOST,app.MAX_BRAKE,hybrid.NATIVE_EVALUATION)
        try:
            app.configure_track('figure_eight',40,cones=False);app.configure_traffic('convoy');app.TRACK.set_backend('rust')
            app.RADAR_MODE='laser2';app.STEERING_BOOST=.5;app.MAX_BRAKE=.7
            actor=LaserVisionNetwork(seed=3).set_backend('rust');actor.randomize()
            traffic=LocalVisionNetwork(ECHO,seed=4).set_backend('rust');traffic.randomize();traffic.metadata['radar_mode']='sectors30echo'
            cars=app.initial();self.assertEqual(len(app.model_observations(actor,cars[0],cars)),366);self.assertEqual(len(app.model_observations(traffic,cars[0],cars)),90)
            hybrid.NATIVE_EVALUATION=False
            py=hybrid.evaluate_candidate(actor,traffic,40,initial_cars=cars,pass_only=True,car_collision_penalty=100.)
            native=evaluate(actor,traffic,40,initial_cars=cars,pass_only=True,car_collision_penalty=100.)
            for a,b in zip(py['roles'],native['roles']):
                for k in ('steps','collision','overtakes'):self.assertEqual(a[k],b[k])
                for k in ('distance','reward'):self.assertAlmostEqual(a[k],b[k],places=7)
        finally:app.TRACK,app.RADAR_MODE,app.STEERING_BOOST,app.MAX_BRAKE,hybrid.NATIVE_EVALUATION=saved
