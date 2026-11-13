import math
import unittest
from games.car.track import Track
from games.car.laser_radar import walls
from games.car.training_tracks import DEFINED_TRACKS
from games.car.multi_track import TrackPool,practice_budgets


def curvatures(track):
    for a,b,c in zip(track.points,track.points[1:],track.points[2:]):
        ab=math.dist(a,b);bc=math.dist(b,c);ac=math.dist(a,c)
        yield 2*((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))/(ab*bc*ac)


class TurnCurriculumTests(unittest.TestCase):
    def test_normal_turns_are_flat_open_and_gentler_in_both_directions(self):
        track=Track.generate('normal_turns');values=list(curvatures(track))
        self.assertFalse(track.closed)
        self.assertEqual({p[2] for p in track.points},{0.})
        self.assertGreater(max(values),.003)
        self.assertLess(min(values),-.003)
        self.assertLess(max(map(abs,values)),max(map(abs,curvatures(Track.generate('tight_turns'))))/2)
        self.assertTrue(all(p[1]==0 for p in track.points if p[0]<=300))
        self.assertEqual(len(walls(track)),2*(len(track.points)-1))

    def test_mirror_reverses_first_turn_from_either_entrance(self):
        original=Track.generate('tight_turns');mirror=Track.generate('tight_turns_mirrored')
        self.assertAlmostEqual(original.perimeter,mirror.perimeter)
        self.assertEqual(mirror.points,tuple((x,-y,z) for x,y,z in original.points))
        for reverse in (False,True):
            a=list(curvatures(original));b=list(curvatures(mirror))
            if reverse:a=[-v for v in reversed(a)];b=[-v for v in reversed(b)]
            first_a=next(v for v in a if abs(v)>1e-5)
            first_b=next(v for v in b if abs(v)>1e-5)
            self.assertLess(first_a*first_b,0.)

    def test_six_tracks_share_existing_attempt_budget_and_evaluate_both_directions(self):
        self.assertEqual(len(DEFINED_TRACKS),6)
        self.assertEqual(sum(n for _,n in practice_budgets(DEFINED_TRACKS,100,1,1)),100)
        pool=TrackPool(DEFINED_TRACKS,1000,42,standard_starts=True)
        starts=pool.starts(12)
        for name in DEFINED_TRACKS:
            self.assertEqual({cars[0]['direction'] for cars in starts[name]},{-1,1})
            self.assertEqual(pool.uses_standard_starts(name),name!='figure_eight')
