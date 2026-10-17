import importlib.util
import unittest
from games.maze.generator import generate
from games.maze.modular.tasks import World, synthetic_batch, labels_at


class ModularTasksTests(unittest.TestCase):
    def test_observations_do_not_reveal_visits_or_reward(self):
        w=World(generate(9,9,seed=7));before=w.observe()
        w.visits[(1,1)]=200;w.last_reward=1000
        self.assertEqual(before,w.observe())
        self.assertEqual(len(before),8)

    def test_synthetic_labels_and_reproducibility(self):
        a,b=synthetic_batch(67,3,5)
        self.assertEqual((a,b),synthetic_batch(67,3,5))
        for seq,labels in zip(a,b):
            for event,label in zip(seq,labels):
                self.assertEqual(len(event),15)
                self.assertEqual(event[8:12].index(1.),label)


@unittest.skipUnless(importlib.util.find_spec('mlx'),'MLX required')
class ModularNetworkTests(unittest.TestCase):
    def test_streaming_state_matches_full_sequence_and_reset(self):
        import mlx.core as mx
        from games.maze.modular.networks import Memory
        mx.random.seed(1);m=Memory()
        x,_=synthetic_batch(8,2,6);x=mx.array(x)
        h,c=m(x);hs=cs=None
        for i in range(8):
            a,b=m(x[:,i:i+1],hs,cs);hs,cs=a[:,0],b[:,0]
        self.assertLess(float(mx.max(mx.abs(hs-h[:,-1]))),1e-5)
        fresh,_=m(x[:,:1]);self.assertLess(float(mx.max(mx.abs(fresh-h[:,:1]))),1e-5)

    def test_decision_training_does_not_update_other_nets(self):
        import mlx.core as mx
        from games.maze.modular.networks import Perception,Memory,Decision,HIDDEN
        from games.maze.modular.train import make_update,observe_batch
        import mlx.nn as nn
        p,m,d=Perception(),Memory(),Decision()
        w=[World(generate(5,5,seed=3))]
        rays,seen,previous,h,c=observe_batch(p,m,w,mx.zeros((1,HIDDEN)),mx.zeros((1,HIDDEN)))
        before=m.lstm.Wx.tolist();perception_before=p.layers.layers[0].weight.tolist()
        update=make_update(d,lambda model,r,s,h,prev:nn.losses.cross_entropy(model(r,s,h,prev),mx.array([0]),reduction='mean'))
        loss=update(rays,seen,h,previous);mx.eval(loss,d.parameters())
        self.assertEqual(before,m.lstm.Wx.tolist())
        self.assertEqual(perception_before,p.layers.layers[0].weight.tolist())
