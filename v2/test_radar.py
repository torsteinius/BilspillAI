import math
import random
import unittest
import demo

class RadarTests(unittest.TestCase):
    def pair(self, angle=math.radians(15), distance=100):
        return (dict(x=400., y=130., heading=0., crashed=False),
                dict(x=400+distance*math.cos(angle), y=130+distance*math.sin(angle), heading=math.pi, crashed=False))

    def test_detects_car_between_rays(self):
        a,b=self.pair()
        self.assertTrue(demo.radar(a,b)['detected'])
        # A centreline ray would miss this car by more than its radius.
        self.assertGreater(abs(b['y']-a['y']),demo.CAR_RADIUS)
        self.assertGreater(demo.radar(a,b)['bearing'],0)
        self.assertEqual(len(demo.observations(a,b)),9)

    def test_behind_out_of_range_and_inactive_are_ignored(self):
        for angle,distance in [(math.pi,100),(0,200),(math.pi/2,100)]:
            a,b=self.pair(angle,distance)
            self.assertFalse(demo.radar(a,b)['detected'])
        a,b=self.pair();b['crashed']=True
        self.assertEqual(demo.radar(a,b)['proximity'],0)

    def test_circle_boundary_and_rotation(self):
        a,b=self.pair()
        b.update(x=490, y=226)  # 96 from bubble centre, touching car radius 7.
        self.assertTrue(demo.radar(a,b)['detected'])
        b['y']=228
        self.assertFalse(demo.radar(a,b)['detected'])
        a['heading']=math.pi/2
        b.update(x=400,y=230)
        r=demo.radar(a,b)
        self.assertTrue(r['detected'])
        self.assertAlmostEqual(r['center_x'],400)
        self.assertAlmostEqual(r['center_y'],220)

    def test_left_right_and_range(self):
        a,b=self.pair(-.3,100)
        self.assertLess(demo.radar(a,b)['bearing'],0)
        a,b=self.pair(0,40)
        self.assertGreater(demo.radar(a,b)['proximity'],.7)

    def test_migration_preserves_old_steering_for_any_radar(self):
        rng=random.Random(1); old=[rng.uniform(-1,1) for _ in range(145)]
        new=demo.migrate_sensor_weights(old)
        for _ in range(20):
            readings=[rng.uniform(0,180) for _ in range(7)]
            values=[1-v/180 for v in readings]; offset=0
            for width in (8,8,1):
                stride=len(values)+1
                values=[math.tanh(sum(old[offset+n*stride+i]*v for i,v in enumerate(values))+old[offset+n*stride+stride-1]) for n in range(width)]
                offset+=width*stride
            self.assertAlmostEqual(demo.policy(new,readings+[rng.random(),rng.uniform(-1,1)]),values[0])
