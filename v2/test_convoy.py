import math
import unittest
from games.car import app


class ConvoyTests(unittest.TestCase):
    def setUp(self):
        app.configure_track('figure_eight', 300)
        app.configure_traffic('convoy')

    def tearDown(self):
        app.configure_traffic('opposite')
        app.configure_track()

    def test_five_speeds_and_starts_spaced_around_entire_lap(self):
        cars = app.initial()
        self.assertEqual(len(cars), 5)
        self.assertEqual([c['speed_factor'] for c in cars], [.8,.9,1.,1.1,1.2])
        self.assertEqual({c['direction'] for c in cars}, {1})
        starts = [app.progress(c['x'],c['y'],c['z']) for c in cars]
        for a,b in zip(starts,starts[1:]+starts[:1]):
            self.assertAlmostEqual((a-b) % app.PERIMETER, app.PERIMETER/5)
        old = [(c['x'],c['y']) for c in cars]
        app.step(cars,[0.]*app.WEIGHT_COUNT)
        for c,p in zip(cars,old):
            self.assertAlmostEqual(math.hypot(c['x']-p[0],c['y']-p[1]),3*c['speed_factor'])

    def test_sensors_and_radar_consider_all_other_cars(self):
        app.configure_track('s_curve')
        car=dict(x=400.,y=130.,heading=0.,crashed=False)
        far=dict(car,x=500.)
        near=dict(car,x=450.)
        behind=dict(car,x=350.)
        traffic=[car,far,behind,near]
        self.assertAlmostEqual(app.sensors(car,traffic)[3],43)
        self.assertEqual(app.radar(car,traffic)['distance'],app.radar(car,near)['distance'])
        self.assertEqual(len(app.radar(car,traffic)['targets']),2)
        self.assertEqual(app.radar(car,list(reversed(traffic))),app.radar(car,traffic))
        self.assertEqual(len(app.observations(car,traffic)),9)
        near['crashed']=True
        self.assertAlmostEqual(app.sensors(car,traffic)[3],93)
        self.assertFalse(app.radar(car,[])['detected'])

    def test_collision_only_restarts_involved_pair(self):
        app.configure_track('s_curve')
        cars=[dict(x=x,y=130.,z=0.,heading=0.,direction=1,travel=0.,crashed=False,restarts=0)
              for x in (220.,300.,380.,460.,470.)]
        _,reason=app.step(cars,[0.]*app.WEIGHT_COUNT)
        self.assertEqual(reason,'Bilene kolliderte')
        self.assertEqual([c['crashed'] for c in cars],[False,False,False,True,True])

    def test_spawn_waits_for_any_car(self):
        cars=app.initial()
        cars[0]['crashed']=True
        cars[4].update(x=cars[0]['x'],y=cars[0]['y'],z=cars[0]['z'])
        app.restart_crashed(cars)
        self.assertTrue(cars[0]['crashed'])
        cars[4]['crashed']=True
        app.restart_crashed(cars)
        self.assertFalse(cars[0]['crashed'])
        self.assertEqual(cars[0]['speed_factor'],.8)
