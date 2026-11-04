import random
import tempfile
import unittest
from pathlib import Path
from ai.network import NeuralNetwork
from ai.branched import BranchedNetwork,MLXBranchedBackend
from scripts.train_branched_maze import sample_starts

class BranchedTests(unittest.TestCase):
    def test_save_reload_and_branch_isolation(self):
        net=BranchedNetwork(seed=17);net.randomize()
        x=[.1]*260
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'net.json';net.save(path);loaded=NeuralNetwork.load(path)
            self.assertEqual(net.forward(x),loaded.forward(x))
            self.assertIsInstance(loaded,BranchedNetwork)
        # With all history-to-merge connections disabled, history cannot affect output.
        offset=60+257*64+65*16+17*4
        for n in range(8):
            for i in range(4,8):net.weights[offset+n*9+i]=0.
        self.assertEqual(net.forward(x),net.forward(x[:4]+[.9]*256))
        self.assertNotEqual(net.forward(x),net.forward([.9]*4+x[4:]))

    def test_gpu_cpu_match_for_multiple_candidates(self):
        try:backend=MLXBranchedBackend()
        except (ImportError,RuntimeError):self.skipTest('MLX unavailable')
        a=BranchedNetwork(seed=1);a.randomize();b=BranchedNetwork(seed=2);b.randomize()
        inputs=[[.1]*260,[.2]*4+[0.]*256,[.5]*260]
        values,_=backend.predict_indexed(backend.prepare(a.architecture,[a.weights,b.weights]),[1,0,1],inputs)
        for got,x,model in zip(values,inputs,[b,a,b]):
            for actual,expected in zip(got,model.forward(x)):self.assertAlmostEqual(actual,expected,places=6)

    def test_unused_history_columns_frozen_without_changing_predictions(self):
        net=BranchedNetwork(seed=1);net.randomize();champ=net.weights[:]
        candidate=[v+.1 for v in champ];x=[.2]*8+[0.]*252
        before=net.forward(x,candidate)
        net.freeze_unused(candidate,champ,8)
        self.assertEqual(before,net.forward(x,candidate))
        self.assertEqual(candidate[60+4],champ[60+4])
        self.assertNotEqual(candidate[60+3],champ[60+3])
        self.assertNotEqual(candidate[60+256],champ[60+256])

    def test_random_starts_only_use_recorded_poses(self):
        route=dict(maze=dict(name='test',rows=['#####','#...E','#####']),
                   samples=[dict(pose=dict(x=x,y=1,heading=1)) for x in (1,2)])
        rng=random.Random(7)
        starts=[sample_starts({(5,3):[route]},rng)[0] for _ in range(30)]
        self.assertEqual({m.start for m in starts},{(1,1),(2,1)})
        self.assertTrue(all(m.heading==1 for m in starts))
