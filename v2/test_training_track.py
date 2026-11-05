import math
import unittest
from unittest.mock import patch
from games.car import app
from games.car.track import Track

class TrainingTrackTests(unittest.TestCase):
    def tearDown(self):
        app.configure_track()
        app.configure_radar(1.)
        app.RADAR_MODE='legacy'

    def test_training_track_has_alternating_turns_and_cones_inside_road(self):
        track=Track.generate('training')
        self.assertEqual(len(track.cones),11)
        signs=[]
        for i,p in enumerate(track.points):
            a,b=track.points[i-1],track.points[(i+1)%len(track.points)]
            cross=(p[0]-a[0])*(b[1]-p[1])-(p[1]-a[1])*(b[0]-p[0])
            if abs(cross)>1e-6:signs.append(cross>0)
        self.assertGreater(sum(a!=b for a,b in zip(signs,signs[1:])),8)
        for cone in track.cones:
            self.assertGreaterEqual(track.clearance(cone['x'],cone['y'])+1e-8,cone['radius']+2*app.CAR_RADIUS)

    def test_cones_are_seen_and_contact_is_penalized(self):
        app.configure_track()
        app.TRACK.cones=[dict(x=450.,y=130.,z=0.,radius=6.,kind='cone',crashed=False)]
        car=dict(x=400.,y=130.,z=0.,heading=0.,direction=1,travel=0.,crashed=False)
        self.assertAlmostEqual(app.sensors(car,[])[3],44.)
        self.assertEqual(app.radar(car,[])['kind'],'cone')
        car['x']=436.
        score,reason=app.step([car],[0.]*app.WEIGHT_COUNT)
        self.assertEqual(reason,'Kjeglekontakt')
        self.assertTrue(car['crashed'])
        self.assertLessEqual(score,-app.COLLISION_PENALTY)

    @patch('games.car.app.clearance', return_value=1000.)
    def test_threefold_radar_and_rotated_side_position(self, _clearance):
        app.configure_radar(3.)
        car=dict(x=0.,y=0.,heading=math.pi/2,crashed=False)
        other=dict(x=-30.,y=400.,crashed=False)
        reading=app.radar(car,[other])
        self.assertEqual(reading['range'],540.)
        self.assertEqual(reading['radius'],270.)
        self.assertTrue(reading['detected'])
        self.assertAlmostEqual(reading['forward'],400.)
        self.assertAlmostEqual(reading['lateral'],30.)
        self.assertAlmostEqual(reading['distance'],math.hypot(400,30)-app.CAR_RADIUS)
        app.configure_radar(1.)
        self.assertFalse(app.radar(car,[other])['detected'])

    def test_spatial_input_has_independent_lateral_position(self):
        app.configure_radar(3.)
        app.RADAR_MODE='spatial'
        car=dict(x=400.,y=130.,heading=0.,crashed=False)
        near=dict(x=500.,y=157.,crashed=False)
        far=dict(x=700.,y=157.,crashed=False)
        a,b=app.observations(car,[near]),app.observations(car,[far])
        self.assertEqual(len(a),9)
        self.assertGreater(a[-2],b[-2])
        self.assertAlmostEqual(a[-1],.1)
        self.assertAlmostEqual(a[-1],b[-1])

    def test_radar_wall_blocks_cars_and_cones_but_not_visible_targets(self):
        track = Track([(0,0), (500,0), (500,200), (0,200)], half_width=38)
        app.configure_radar(3.)
        car = dict(x=200., y=0., z=0., heading=math.pi/2, crashed=False)
        hidden = dict(x=200., y=200., z=0., crashed=False)
        visible = dict(x=210., y=20., z=0., crashed=False)
        with patch.object(app, 'clearance', track.clearance):
            self.assertFalse(app.radar(car, [hidden])['detected'])
            hidden.update(kind='cone', radius=6.)
            self.assertFalse(app.radar(car, [hidden])['detected'])
            reading = app.radar(car, [hidden, visible])
            self.assertTrue(reading['detected'])
            self.assertEqual(len(reading['targets']), 1)
            self.assertEqual(reading['kind'], 'car')

    def test_radar_sightline_follows_ramp_elevation(self):
        track = Track([(0,0,0), (500,0,50), (500,200,50), (0,200,0)])
        car = dict(x=50., y=0., z=5., heading=0., crashed=False)
        target = dict(x=350., y=0., z=35., crashed=False)
        with patch.object(app, 'clearance', track.clearance):
            self.assertTrue(app.radar_line_of_sight(car, target))
