"""Geometry and simulation contracts for generated roads and overpasses."""
import math
import random
import unittest
from games.car.track import Track, project
from games.car import app


class GeneratedTrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.road = Track.generate('figure_eight')

    def test_original_layouts_are_available(self):
        oval = Track.generate('oval')
        self.assertAlmostEqual(oval.perimeter, 560+280*math.pi, delta=.04)
        self.assertTrue(all(p[2] == 0 for p in oval.points))
        self.assertEqual(Track.generate().points[0], (200., 130., 0.))

    def test_quarter_scale_preserves_shape_and_road_width(self):
        self.assertAlmostEqual(self.road.perimeter, 28636.53208441455/4, places=3)
        self.assertEqual(self.road.half_width, 38.)
        signs = []
        for i,p in enumerate(self.road.points):
            a,b = self.road.points[i-1], self.road.points[(i+1)%len(self.road.points)]
            u,v = (p[0]-a[0],p[1]-a[1]), (b[0]-p[0],b[1]-p[1])
            cross = u[0]*v[1]-u[1]*v[0]
            if abs(cross)>1e-8:
                signs.append(cross>0)
                radius = math.hypot(*u)*math.hypot(*v)*math.hypot(b[0]-a[0],b[1]-a[1])/(2*abs(cross))
                self.assertGreater(radius, 25.)
        self.assertGreaterEqual(sum(a!=b for a,b in zip(signs,signs[1:])), 8)
        self.assertLess(max(abs(s[7])/math.sqrt(s[4]) for s in self.road.segments), .20)

    def test_crossing_has_distinct_height_and_progress(self):
        upper,lower = self.road.locate(0,0,40), self.road.locate(0,0,0)
        self.assertAlmostEqual(upper[0],0)
        self.assertAlmostEqual(lower[0],0)
        self.assertAlmostEqual(upper[2]-lower[2],40)
        self.assertAlmostEqual(upper[1],0)
        self.assertGreater(lower[1],self.road.perimeter*.4)
        self.assertLess(lower[1],self.road.perimeter*.6)
        for along in (0, lower[1]):
            for shift in (-12,-3,3,12):
                p = self.road.pose(along+shift)
                actual = self.road.progress(p['x'],p['y'],p['z'])
                error = (actual-along-shift+self.road.perimeter/2)%self.road.perimeter-self.road.perimeter/2
                self.assertAlmostEqual(error,0,places=6)

    def test_spatial_index_matches_full_scan_including_ramps(self):
        rng = random.Random(4)
        for _ in range(40):
            p = self.road.pose(rng.random()*self.road.perimeter, rng.uniform(-80,80))
            x,y,z = p['x'],p['y'],p['z']+rng.uniform(-50,50)
            expected=[]
            for s in self.road.segments:
                square,t = project(x,y,s)
                height = s[6]+t*s[7]
                expected.append((square+(z-height)**2, math.sqrt(square),s[5]+t*s[8],height))
            best=min(expected)
            actual=self.road.locate(x,y,z)
            for a,b in zip(actual[:3],best[1:]):
                self.assertAlmostEqual(a,b,places=6)

    def test_closed_pose_and_invalid_geometry(self):
        self.assertEqual(self.road.pose(0),self.road.pose(self.road.perimeter))
        for points in ([(0,0),(1,1)], [(0,0,0),(0,0,4),(1,1,0)]):
            with self.assertRaises(ValueError):
                Track(points)

    def test_camera_pitch_matches_slope_and_travel_direction(self):
        road = Track([(0,0,0), (100,0,20), (100,100,20), (0,100,0)])
        self.assertAlmostEqual(road.pitch(50,0,10,0), math.atan(.2))
        self.assertAlmostEqual(road.pitch(50,0,10,math.pi), -math.atan(.2))
        self.assertAlmostEqual(road.pitch(50,0,10,math.pi/2), 0)
        self.assertEqual(self.road.pitch(0,0,40,0), 0)
        self.assertEqual(self.road.pitch(0,0,0,0), 0)

    def test_nonlocal_road_overlaps_have_bridge_clearance(self):
        # Check the densely sampled road footprint, not just centreline
        # intersections: remote road strips must not touch on the same level.
        grid, overlaps = {}, 0
        for i,p in enumerate(self.road.points):
            cx,cy = math.floor(p[0]/100), math.floor(p[1]/100)
            for x in range(cx-1,cx+2):
                for y in range(cy-1,cy+2):
                    for j in grid.get((x,y), []):
                        delta = abs(self.road.starts[i]-self.road.starts[j])
                        if min(delta,self.road.perimeter-delta) < 4*self.road.half_width:
                            continue
                        segment = self.road.segments[j]
                        square,t = project(p[0],p[1],segment)
                        if square < (2*self.road.half_width+12)**2:
                            overlaps += 1
                            height = segment[6]+t*segment[7]
                            self.assertGreater(abs(p[2]-height), 36)
            grid.setdefault((cx,cy), []).append(i)
        self.assertGreater(overlaps, 0)


class OverpassSimulationTests(unittest.TestCase):
    def setUp(self):
        app.configure_track('figure_eight', 30)

    def tearDown(self):
        app.configure_track()

    def pair(self, elevation=0):
        a = dict(app.TRACK.pose(0), direction=1,travel=0.,crashed=False,restarts=0)
        b = dict(a, z=elevation, heading=-a['heading'])
        return a,b

    def test_other_deck_is_not_a_sensor_obstacle(self):
        a,b = self.pair()
        absent = dict(b,crashed=True)
        self.assertEqual(app.sensors(a,b),app.sensors(a,absent))
        self.assertFalse(app.radar(a,b)['detected'])
        self.assertFalse(app.radar(b,a)['detected'])
        same = dict(b,z=40)
        self.assertEqual(app.sensors(a,same)[3],0)
        self.assertTrue(app.radar(a,same)['detected'])

    def test_crossing_does_not_open_a_hole_in_walls(self):
        for z in (0,40):
            a,b=self.pair(z)
            segment = app.TRACK.locate(0,0,z)[3]
            a.update(z=z,heading=math.atan2(segment[3],segment[2]))
            b['crashed']=True
            rays=app.sensors(a,b)
            self.assertAlmostEqual(rays[0],app.HALF_WIDTH,delta=.3)
            self.assertAlmostEqual(rays[6],app.HALF_WIDTH,delta=.3)

    def test_crossing_cars_do_not_collide_or_jump_decks(self):
        cars=list(self.pair())
        _,reason=app.step(cars,[0.]*app.WEIGHT_COUNT)
        self.assertEqual(reason,'')
        self.assertEqual([c['z'] for c in cars],[40.,0.])
        self.assertTrue(all(abs(c['travel'])<4 for c in cars))
        cars=list(self.pair(40))
        _,reason=app.step(cars,[0.]*app.WEIGHT_COUNT)
        self.assertEqual(reason,'Bilene kolliderte')

    def test_height_follows_ramp_without_changing_observation_shape(self):
        index=next(i for i,p in enumerate(app.TRACK.points) if 15<p[2]<25)
        a=dict(app.TRACK.pose(app.TRACK.starts[index]),direction=1,travel=0.,crashed=False,restarts=0)
        b=dict(a,crashed=True)
        before=a['z']
        app.step([a,b],[0.]*app.WEIGHT_COUNT)
        self.assertLess(a['z'],before)
        self.assertEqual(len(app.observations(a,b)),9)
        self.assertFalse(a['crashed'])

    def test_ramp_traffic_is_visible_despite_elevation_difference(self):
        index=next(i for i,p in enumerate(app.TRACK.points) if 15<p[2]<25)
        a=dict(app.TRACK.pose(app.TRACK.starts[index]),crashed=False)
        b=dict(app.TRACK.pose(app.TRACK.starts[index]+140),crashed=False)
        self.assertGreater(abs(a['z']-b['z']), 2*app.CAR_RADIUS)
        self.assertTrue(app.radar(a,b)['detected'])
