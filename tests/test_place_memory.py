import importlib.util
import random
import unittest
from games.maze.place_memory.task import make_places,sample_sequence
from games.maze.junction.task import is_landmark,landmark_kind


class PlaceTaskTests(unittest.TestCase):
    def test_queries_only_landmarks_and_labels_precede_write(self):
        places=make_places(61)
        for x,y in places['points']:
            self.assertTrue(is_landmark(landmark_kind(places['maze'],x,y)))
        ids,labels=sample_sequence(places,100,random.Random(8))
        for i,(point,label) in enumerate(zip(ids,labels)):
            self.assertEqual(bool(label),point in ids[:i])
        self.assertEqual(labels[0],0)
        self.assertTrue(all(len(row)==8 for row in places['readings']))


@unittest.skipUnless(importlib.util.find_spec('mlx'),'MLX required')
class PlaceMemoryTests(unittest.TestCase):
    def test_answer_before_write_and_closed_gate_preserves_state(self):
        import mlx.core as mx
        from games.maze.place_memory.network import PlaceMemory,HIDDEN
        model=PlaceMemory();x=mx.ones((2,8))*.2
        h=mx.ones((2,HIDDEN))*.1;c=mx.ones_like(h)*.3
        off,h0,c0=model.step(x,mx.array([False,False]),h,c)
        on,h1,c1=model.step(x,mx.array([True,True]),h,c)
        self.assertEqual(off.tolist(),on.tolist())
        self.assertEqual(h0.tolist(),h.tolist());self.assertEqual(c0.tolist(),c.tolist())
        self.assertNotEqual(h1.tolist(),h.tolist())

    def test_reset_prevents_cross_episode_information(self):
        import mlx.core as mx
        from games.maze.place_memory.network import PlaceMemory
        model=PlaceMemory();x=mx.ones((1,3,8))*.2;g=mx.ones((1,3),dtype=mx.bool_)
        a=model(x,g,True).tolist()[0]
        self.assertAlmostEqual(a[0],a[1]);self.assertAlmostEqual(a[1],a[2])
        first=model(x,g).tolist()[0][0]
        self.assertAlmostEqual(first,a[0])

class RandomHeadingTests(unittest.TestCase):
    def test_each_orientation_changes_sensor_frame(self):
        from games.maze.memory import ANGLES
        p=make_places(99,21)
        for (x,y),poses in zip(p['points'],p['oriented_readings']):
            for heading in range(4):
                expected=[p['maze'].ray(x,y,heading,a)/p['maze'].sensor_range for a in ANGLES]
                self.assertEqual(poses[heading],expected)

    def test_random_headings_and_location_labels_are_independent(self):
        from games.maze.place_memory.task import sample_headings
        ids,labels=sample_sequence({'points':[(1,1)]},20,random.Random(3))
        headings=sample_headings(20,random.Random(4))
        self.assertEqual(set(headings),{0,1,2,3})
        self.assertEqual(labels,[0.]+[1.]*19)

    @unittest.skipUnless(importlib.util.find_spec('mlx'),'MLX required')
    def test_recording_uses_random_pose_and_saved_weights(self):
        from games.maze.place_memory.app import recording
        from games.maze.place_memory.network import PlaceMemory
        from games.maze.junction.model import JunctionDetector
        r=recording(PlaceMemory(),JunctionDetector(),75,length=20)
        self.assertGreater(len(set(f['heading'] for f in r['frames'])),1)
        self.assertEqual(r['frames'][0]['memory_before'],0.)
