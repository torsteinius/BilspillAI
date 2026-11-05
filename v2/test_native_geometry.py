import math
import random
import unittest
from games.car import app
from games.car.track import Track
try:
    from bilspill_ai_native import RoadGeometry
except ImportError:
    RoadGeometry = None

@unittest.skipIf(RoadGeometry is None, 'Native geometry is not installed')
class NativeGeometryTests(unittest.TestCase):
    def tearDown(self):
        app.configure_track()

    def test_geometry_matches_python_on_all_tracks(self):
        rng=random.Random(52)
        for name in Track.NAMES:
            python=Track.generate(name)
            native=Track.generate(name).set_backend('rust')
            for _ in range(150):
                pose=python.pose(rng.random()*python.perimeter, rng.uniform(-80,80))
                x,y,z=pose['x'],pose['y'],pose['z']+rng.uniform(-20,20)
                for a,b in zip(python.locate(x,y,z)[:3],native.locate(x,y,z)[:3]):
                    self.assertAlmostEqual(a,b,places=8)

    def test_rays_match_with_cars_cones_and_elevation(self):
        rng=random.Random(73)
        for name in Track.NAMES:
            app.configure_track(name)
            for _ in range(40):
                car=dict(app.TRACK.pose(rng.random()*app.PERIMETER,rng.uniform(-30,30)),crashed=False)
                car['heading']+=rng.uniform(-math.pi,math.pi)
                target=dict(car,x=car['x']+20,y=car['y']+15)
                app.TRACK.set_backend('python')
                expected=app.sensors(car,[target])
                app.TRACK.set_backend('rust')
                actual=app.sensors(car,[target])
                for a,b in zip(expected,actual):
                    self.assertAlmostEqual(a,b,places=8)
