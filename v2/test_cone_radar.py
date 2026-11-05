import math
import unittest
from unittest.mock import patch
from games.car import app

class ConeRadarTests(unittest.TestCase):
    def setUp(self):
        self.mode = app.RADAR_MODE
        app.RADAR_MODE = 'cone'
        app.configure_radar(3.)
        self.car = dict(x=400., y=130., heading=0., crashed=False, speed_factor=1.)

    def tearDown(self):
        app.RADAR_MODE = self.mode
        app.configure_radar(1.)

    def target(self, x=500., y=130., **extra):
        return dict(x=x, y=y, heading=0., crashed=False, **extra)

    def test_sector_range_rotation_and_no_wall_queries(self):
        with patch.object(app, 'clearance', side_effect=AssertionError('wall queried')):
            self.assertTrue(app.radar(self.car, self.target())['detected'])
            for target in [self.target(x=300.), self.target(x=950.), self.target(x=410., y=230.)]:
                self.assertFalse(app.radar(self.car, target)['detected'])
            self.car['heading'] = math.pi/2
            self.assertTrue(app.radar(self.car, self.target(x=400., y=230.))['detected'])

    def test_nearest_object_motion_and_side(self):
        slow = self.target(x=500., y=130., speed_factor=.8)
        result = app.radar(self.car, [self.target(x=600.), slow])
        self.assertAlmostEqual(result['distance'], 93.)
        self.assertAlmostEqual(result['speed'], 2.4)
        self.assertAlmostEqual(result['closing_speed'], .6)
        fast = self.target(speed_factor=1.2)
        self.assertAlmostEqual(app.radar(self.car, fast)['closing_speed'], -.6)
        self.assertGreater(app.radar(self.car, self.target(y=150.))['lateral'], 0.)
        self.assertLess(app.radar(self.car, self.target(y=110.))['lateral'], 0.)

    def test_stationary_cone_and_empty_observation(self):
        cone = self.target(kind='cone', radius=6.)
        result = app.radar(self.car, cone)
        self.assertEqual(result['speed'], 0.)
        self.assertAlmostEqual(result['closing_speed'], 3.)
        with patch.object(app, 'sensors', return_value=[180.]*7):
            self.assertEqual(len(app.observations(self.car, cone)), 11)
            self.assertEqual(app.observations(self.car, [])[-4:], [0.]*4)
