import math
import unittest
from unittest.mock import patch

from ai.laser_vision import LaserVisionNetwork
from ai.local_vision import LocalVisionNetwork, ECHO
from ai.rust_backend import native_module
from games.car import app, hybrid
from games.car.laser_radar import ray_angles, walls, road_triangles
from games.car.native_evaluation import evaluate
from games.car.track import Track


class VerticalFanTests(unittest.TestCase):
    def test_constant_slopes_match_flat_road_exactly(self):
        baseline=None
        for grade in (0.,-.19,.19):
            left=[(-600.,-38.,-600*grade),(600.,-38.,600*grade)]
            right=[(-600.,38.,-600*grade),(600.,38.,600*grade)]
            radar=native_module().LaserRadar([(*left[0],*left[1]),(*right[0],*right[1])],ray_angles())
            radar.set_ground([(left[0],left[1],right[1]),(left[0],right[1],right[0])])
            rows=radar.scan_fan(0.,0.,0.,0.,math.atan(grade),3.,540.,[],math.radians(12))
            if baseline is None:baseline=rows
            self.assertEqual(sum(r[4]==0 for r in rows[:61]),58)
            for actual,expected in zip(rows,baseline):
                self.assertAlmostEqual(actual[0],expected[0],places=9)
                self.assertEqual(actual[4],expected[4])

    def test_finds_forward_curb_after_downhill_slope_changes(self):
        track=Track.generate('figure_eight').set_backend('rust')
        segment=track.segments[170]
        car=track.pose(segment[5]+segment[8]/2)
        pitch=track.pitch(car['x'],car['y'],car['z'],car['heading'])
        radar=native_module().LaserRadar(walls(track),ray_angles())
        radar.set_ground(road_triangles(track))
        args=(car['x'],car['y'],car['z'],car['heading'],pitch,3.,540.,[])
        old=radar.scan(*args);new=radar.scan_fan(*args,math.radians(12))
        front=[i for i,a in enumerate(ray_angles()) if abs(a)<math.radians(30)]
        self.assertEqual(sum(old[i][4]==0 for i in front),0)
        self.assertGreater(sum(new[i][4]==0 for i in front),10)
        self.assertEqual(old[40][4],-1)
        self.assertEqual(new[40][4],0)
        self.assertLess(new[40][0],100.)
        # Enabling the new mode must not mutate the legacy scan configuration.
        self.assertEqual(radar.scan(*args),old)

    def test_asphalt_blocks_hidden_curb_and_is_not_clear_space(self):
        radar=native_module().LaserRadar([(40.,-20.,0.,40.,20.,0.)],[0.])
        radar.set_ground([((15.,-30.,0.),(25.,-30.,10.),(25.,30.,10.)),
                          ((15.,-30.,0.),(25.,30.,10.),(15.,30.,0.))])
        args=(0.,0.,0.,0.,0.,3.,100.,[])
        self.assertEqual(radar.scan(*args)[0][4],0)
        row=radar.scan_fan(*args,math.radians(12))[0]
        self.assertEqual(row[4],3)  # opaque road, not a wall seen through it
        self.assertGreater(row[0],15.)
        self.assertLess(row[0],25.)

    def test_fan_requires_valid_road_geometry_and_angle(self):
        radar=native_module().LaserRadar([], [0.])
        with self.assertRaises(ValueError):
            radar.scan_fan(0.,0.,0.,0.,0.,3.,100.,[],.2)
        with self.assertRaises(ValueError):
            radar.set_ground([((0.,0.,0.),(0.,0.,0.),(0.,0.,0.))])

    def test_native_evaluation_matches_python_with_fan_and_ramp(self):
        track=Track.generate('figure_eight').set_backend('rust')
        actor=LaserVisionNetwork(seed=3).set_backend('rust');actor.randomize()
        actor.metadata.update(laser_vertical_fan_degrees=12.,observation_version='laser2_distance_closing_echo_fan_v2')
        traffic=LocalVisionNetwork(ECHO,seed=4).set_backend('rust');traffic.randomize()
        traffic.metadata['radar_mode']='sectors30echo'
        with patch.object(app,'TRACK',track),patch.object(app,'PERIMETER',track.perimeter),patch.object(app,'progress',track.progress),patch.object(app,'clearance',track.clearance),patch.object(app,'RADAR_MODE','laser2'),patch.object(app,'ROAD_ONLY',True),patch.object(app,'RADAR_RANGE',540.),patch.object(app,'TRAFFIC','convoy'),patch.object(hybrid,'NATIVE_EVALUATION',False):
            cars=app.initial()
            segment=track.segments[170]
            cars[0].update(track.pose(segment[5]+segment[8]/2))
            kwargs=dict(initial_cars=cars,pass_only=True)
            python=hybrid.evaluate_candidate(actor,traffic,35,**kwargs)
            rust=evaluate(actor,traffic,35,**kwargs)
            for before,after in zip(python['roles'],rust['roles']):
                for key in ('steps','collision'):self.assertEqual(before[key],after[key])
                for key in ('distance','reward'):self.assertAlmostEqual(before[key],after[key],places=7)
