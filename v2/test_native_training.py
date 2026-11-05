"""Cross-engine parity for training gradients, radar and continuous collisions."""
import copy
import math
import random
import unittest
from ai.network import NeuralNetwork
from ai.rust_backend import native_module
from games.car import app
from games.car.temporal import forward_gradient, forward_latent


class NativeTrainingTests(unittest.TestCase):
    def setUp(self):
        self.saved = {name:getattr(app,name) for name in ('TRACK','clearance','progress','PERIMETER','PATH','HALF_WIDTH','SIMULATION_STEPS','cars','RADAR_MODE','RADAR_RANGE','RADAR_RADIUS','RADAR_OFFSET','RADAR_SCALE','TRAFFIC')}
        self.saved_status = app.status.copy()
        self.rng = random.Random(771)

    def tearDown(self):
        for name,value in self.saved.items():setattr(app,name,value)
        app.status.clear();app.status.update(self.saved_status)

    def assertNested(self, a, b):
        if isinstance(a, dict):
            self.assertEqual(a.keys(), b.keys())
            for k in a:self.assertNested(a[k], b[k])
        elif isinstance(a, (tuple, list)):
            self.assertEqual(len(a),len(b))
            for x,y in zip(a,b):self.assertNested(x,y)
        elif isinstance(a, float):self.assertAlmostEqual(a,b,places=9)
        else:self.assertEqual(a,b)

    def test_gradients_and_latent(self):
        for arch in ([3,2], [3,5,2], [23,8,8,8,8,2], [23,8,8,8,8,1]):
            n=NeuralNetwork(arch)
            n.weights=[self.rng.uniform(-.5,.5) for _ in n.weights]
            for _ in range(5):
                inputs=[self.rng.uniform(-1,1) for _ in range(arch[0])]
                n.set_backend('python')
                expected=[forward_gradient(n,inputs,i) for i in range(arch[-1])]
                n.set_backend('rust')
                self.assertNested(expected,[forward_gradient(n,inputs,i) for i in range(arch[-1])])
                self.assertNested([row[0] for row in expected],forward_latent(n,inputs))
                # Independent finite difference on an output weight.
                j=len(n.weights)-1;old=n.weights[j];eps=1e-6
                n.weights[j]=old+eps;a=forward_latent(n,inputs)[-1]
                n.weights[j]=old-eps;b=forward_latent(n,inputs)[-1];n.weights[j]=old
                self.assertAlmostEqual(expected[-1][1][j],(a-b)/(2*eps),places=7)

    def test_batched_swept_collisions(self):
        for _ in range(40):
            old=[tuple(self.rng.uniform(-30,30) for _ in range(3)) for _ in range(5)]
            new=[tuple(self.rng.uniform(-30,30) for _ in range(3)) for _ in range(5)]
            cones=[(0.,0.,0.,6.),(10.,-5.,40.,6.)]
            cg,pg=native_module().separations(old,new,cones,7.)
            cars=[dict(zip(('x','y','z'),p)) for p in new]
            for i in range(5):
                for j in range(5):self.assertAlmostEqual(pg[i][j],app.swept_distance([old[i],old[j]],[cars[i],cars[j]])-14.,places=10)
                for j,(x,y,z,r) in enumerate(cones):
                    self.assertAlmostEqual(cg[i][j],app.swept_distance([old[i],(x,y,z)],[cars[i],dict(x=x,y=y,z=z)])-7-r,places=10)

    def test_radar_boundaries_padding_and_overpass(self):
        app.configure_track('figure_eight',1000);app.configure_radar(3.)
        for mode in ('cone','cone4','cone4relative'):
            app.RADAR_MODE=mode
            for _ in range(20):
                car=dict(x=0.,y=0.,z=0.,heading=self.rng.uniform(-math.pi,math.pi),speed=2.,crashed=False)
                objects=[dict(x=self.rng.uniform(-550,550),y=self.rng.uniform(-550,550),z=self.rng.choice([0.,40.]),heading=self.rng.random()*6,speed=self.rng.random()*3,kind='car',crashed=False,target_id=str(i)) for i in range(20)]
                objects += [dict(x=100*math.cos(car['heading']+angle),y=100*math.sin(car['heading']+angle),heading=0.,kind='cone',crashed=False) for angle in (-math.pi/3-.001,-math.pi/3+.001,math.pi/3-.001,math.pi/3+.001)]
                app.TRACK.set_backend('python');a=app.radar(car,objects)
                app.TRACK.set_backend('rust');b=app.radar(car,objects)
                self.assertNested(a,b)

    def test_whole_step_events_and_rewards(self):
        app.configure_track('training',1000);app.configure_traffic('convoy')
        cars=app.initial(0)
        for _ in range(70):
            controls=[(self.rng.uniform(-1,1),self.rng.random()) for c in cars]
            a=copy.deepcopy(cars);b=copy.deepcopy(cars);ea=[];eb=[]
            app.TRACK.set_backend('python');ra=app.step(a,[],controls=controls,events=ea)
            app.TRACK.set_backend('rust');rb=app.step(b,[],controls=controls,events=eb)
            self.assertNested(ra,rb);self.assertNested(a,b);self.assertEqual(ea,eb)
            cars=b
            app.restart_crashed(cars,0)
