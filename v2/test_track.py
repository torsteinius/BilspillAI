import math
import random
import unittest
import track

class TrackTests(unittest.TestCase):
    def test_spatial_search_matches_full_geometry(self):
        rng = random.Random(12)
        for _ in range(100):
            x,y=rng.uniform(0,800),rng.uniform(0,540)
            expected=min(track.project(x,y,s)[0] for s in track.SEGMENTS)**.5
            self.assertAlmostEqual(track.nearest(x,y)[0],expected,places=8)

    def test_centerline_clearance_and_turns_in_both_directions(self):
        signs=set()
        points=track.POINTS
        for i,p in enumerate(points):
            self.assertAlmostEqual(track.clearance(*p),track.HALF_WIDTH,places=7)
            a,b=points[i-1],points[(i+1)%len(points)]
            cross=(p[0]-a[0])*(b[1]-p[1])-(p[1]-a[1])*(b[0]-p[0])
            if abs(cross)>1e-6: signs.add(cross>0)
        self.assertEqual(signs,{True,False})
