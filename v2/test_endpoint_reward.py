import math
import unittest
from games.car.progress_reward import begin_window,advance_window


class EndpointRewardTests(unittest.TestCase):
    def test_curve_uses_chord_not_sum_of_segments(self):
        car=dict(x=10.,y=0.,z=0.,travel=0.)
        window=begin_window(car)
        for i in range(1,11):
            angle=math.pi/2*i/10
            car.update(x=10*math.cos(angle),y=10*math.sin(angle),travel=10*angle)
            distance,weighted=advance_window(window,car,2.)
        self.assertAlmostEqual(distance,math.sqrt(200))
        self.assertAlmostEqual(weighted,2*math.sqrt(200))
        self.assertLess(distance,10*math.pi/2)

    def test_closed_loop_gets_zero_even_if_reported_path_progress_is_positive(self):
        car=dict(x=10.,y=0.,travel=0.)
        window=begin_window(car)
        for i in range(1,11):
            car.update(x=10*math.cos(math.tau*i/10),y=10*math.sin(math.tau*i/10),travel=i*5.)
            distance,reward=advance_window(window,car,3.)
        self.assertAlmostEqual(distance,0.)
        self.assertAlmostEqual(reward,0.)

    def test_partial_window_averages_factors_and_includes_elevation(self):
        car=dict(x=0.,y=0.,z=0.,travel=0.)
        window=begin_window(car)
        car.update(x=1.,z=1.,travel=1.)
        self.assertEqual(advance_window(window,car,1.),(0.,0.))
        car.update(x=3.,z=4.,travel=5.)
        self.assertEqual(advance_window(window,car,3.,terminal=True),(5.,10.))
        self.assertEqual(advance_window(window,car,3.,terminal=True),(0.,0.))

    def test_reverse_motion_is_not_rewarded(self):
        car=dict(x=0.,y=0.,travel=0.)
        window=begin_window(car)
        car.update(x=-10.,travel=-10.)
        self.assertEqual(advance_window(window,car,3.,terminal=True),(0.,0.))
