import importlib.util
from pathlib import Path
import unittest
from games.maze.world import Maze
from games.maze.generator import generate
from games.maze.junction.task import landmark_kind,stop_reward,walk
from games.maze.training import Trainer,Config


class JunctionTests(unittest.TestCase):
    def maze(self,rows):
        return Maze('test',tuple(rows),(1,1))

    def test_corner_straight_branch_and_dead_end(self):
        m=self.maze(['#######','#.....E','#.###.#','#.....#','#######'])
        self.assertEqual(landmark_kind(m,1,1),'hjørne')
        self.assertEqual(landmark_kind(m,2,1),'rett korridor')
        self.assertEqual(landmark_kind(m,5,1),'forgrening')
        m=self.maze(['#####','#...E','#####'])
        self.assertEqual(landmark_kind(m,1,1),'blindvei')
        self.assertEqual(stop_reward(True,'hjørne'),1)
        self.assertEqual(stop_reward(True,'rett korridor'),-1)
        self.assertEqual(stop_reward(False,'hjørne'),0)

    def test_detector_sampling_does_not_change_legacy_movement(self):
        t=Trainer(Config(learned_memory=True,start_in_field=False),Path('/tmp/unused-junction-test.json'))
        maze=generate(9,9,seed=9)
        before=t.network.weights[:]
        samples,e=walk(t,maze)
        legacy=t.rollout(maze,t.network.weights)
        self.assertEqual(e.actions,legacy.actions)
        self.assertEqual(e.history,legacy.history)
        self.assertEqual(e.score,legacy.score)
        self.assertEqual(before,t.network.weights)
        self.assertEqual(len(samples[0]['rays']),8)

    @unittest.skipUnless(importlib.util.find_spec('mlx'),'MLX required')
    def test_reward_gradient_encourages_correct_stop(self):
        import mlx.core as mx
        from games.maze.junction.model import JunctionDetector
        from games.maze.modular.train import make_update
        mx.random.seed(4);model=JunctionDetector()
        x=mx.array([[.05]*8,[.5]*8]);rewards=mx.array([1.,-1.])
        initial=model(x).tolist()
        update=make_update(model,lambda m,x,r:-mx.mean(m(x)*r),.01)
        for _ in range(40):
            loss=update(x,rewards);mx.eval(loss,model.parameters())
        result=model(x).tolist()
        self.assertGreater(result[0],initial[0])
        self.assertLess(result[1],initial[1])
