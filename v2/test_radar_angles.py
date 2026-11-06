import math
import unittest
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car import app
from games.car.hybrid import add_radar_angles


class RadarAnglesTests(unittest.TestCase):
    def test_angles_are_ego_relative_including_velocity(self):
        car=dict(x=0.,y=0.,heading=0.,speed=3.)
        other=dict(x=100.,y=100.,heading=math.pi/2,speed=3.)
        bearing,motion=app.radar_angles(car,other)
        self.assertAlmostEqual(bearing,math.pi/4)
        self.assertAlmostEqual(motion,3*math.pi/4)
        rotated_car=dict(car,heading=math.pi/2)
        rotated_other=dict(other,x=-100.,y=100.,heading=math.pi)
        b,m=app.radar_angles(rotated_car,rotated_other)
        self.assertAlmostEqual(b,bearing);self.assertAlmostEqual(m,motion)
        self.assertEqual(app.radar_angles(car,dict(other,heading=0.,speed=3.))[1],0.)
        self.assertAlmostEqual(abs(app.radar_angles(car,dict(other,kind='cone'))[1]),math.pi)

    def test_expansion_preserves_old_connections_and_biases(self):
        old=NeuralNetwork([23,8,8,8,8,3],seed=1)
        old.weights=[math.sin(i)*.3 for i in range(old.weight_count)]
        new=add_radar_angles(old,20)
        self.assertEqual(new.architecture,(31,8,8,8,8,3))
        self.assertEqual(len(new.weights),len(old.weights)+64)
        for n in range(8):
            self.assertEqual(new.weights[n*32:n*32+23],old.weights[n*24:n*24+23])
            self.assertEqual(new.weights[n*32+31],old.weights[n*24+23])
        self.assertEqual(new.weights[8*32:],old.weights[8*24:])
        self.assertNotEqual(new.weights[23:31],[0.]*8)
        for backend in ('python','rust'):
            old.set_backend(backend);new.set_backend(backend)
            for value in (0.,.5,-1.):
                self.assertEqual(new.forward([value]*23+[0.]*8),old.forward([value]*23))

    def test_four_targets_append_angles_without_changing_old_inputs(self):
        car=dict(x=0.,y=0.,heading=0.,speed=3.,crashed=False)
        targets=[dict(x=100.+i*30,y=(-1)**i*20.,heading=.2*i,speed=2.+i*.2,crashed=False,target_id=str(i)) for i in range(5)]
        with patch.object(app,'RADAR_RANGE',540.),patch.object(app.TRACK,'cones',[]),patch.object(app,'same_level',return_value=True),patch.object(app,'sensors',return_value=[100.]*7):
            results=[]
            for native in (False,True):
                from ai.rust_backend import native_module
                with patch.object(app,'NATIVE_CAR_KERNELS',native),patch.object(app.TRACK,'native',object()),patch.object(app,'RADAR_MODE','cone4relative'):
                    old=app.observations(car,[car]+targets)
                    with patch.object(app,'RADAR_MODE','cone4angles'):
                        new=app.observations(car,[car]+targets)
                        self.assertEqual(new[:23],old)
                        self.assertEqual(len(new),31)
                        self.assertEqual(app.observations(car,[car])[7:],[0.]*24)
                        short=app.observations(car,[car,targets[0]])
                        self.assertEqual(short[25:],[0.]*6)
                        for i,target in enumerate(targets[:4]):
                            for j,angle in enumerate(app.radar_angles(car,target)):
                                self.assertAlmostEqual(new[23+2*i+j],angle/math.pi)
                        results.append(new)
            for a,b in zip(*results):self.assertAlmostEqual(a,b)
