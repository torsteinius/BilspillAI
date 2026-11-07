import unittest,math
from unittest.mock import patch
from games.car import app
from v2 import test_radar_echo

class SteeringCurveTests(unittest.TestCase):
    def test_center_and_full_lock(self):
        app.configure_track()
        with patch.object(app,'STEERING_BOOST',.5):
            for steer in (-1.,-.5,-.1,0.,.1,.5,1.):
                car=dict(x=400.,y=130.,z=0.,heading=0.,direction=1,travel=0.,crashed=False,speed_factor=1.)
                app.step([car],[],controls=[steer])
                self.assertAlmostEqual(car['heading'],.045*(steer+.5*steer**3))
            self.assertAlmostEqual(.045*(1+.5),.0675)
            self.assertAlmostEqual((.1+.5*.1**3)/.1,1.005)
    def test_native_matches_reference_with_curve(self):
        with patch.object(app,'STEERING_BOOST',.5):
            test_radar_echo.EchoTests('test_native_reference_evaluation_with_echo').test_native_reference_evaluation_with_echo()
