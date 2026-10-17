import tempfile
import unittest
from pathlib import Path
from games.maze.world import Maze, Rules
from games.maze.memory import MemoryEpisode
from games.maze.training import Config, Trainer


class MemoryTests(unittest.TestCase):
    def episode(self, **kw):
        return MemoryEpisode(Maze('test', ('#####', '#...E', '#...#', '#...#', '#####'), (1, 1)), Rules(memory_steps=2, revisit_penalty=.05, **kw))

    def test_write_gate_zero_occupancy_capacity_and_reset(self):
        e = self.episode()
        e.apply_outputs([0, 1, 0, 0, 0, 1])
        self.assertEqual(e.memory, [])
        e.apply_outputs([0, 1, 0, 0, 1, 0])
        self.assertEqual(e.memory, [0])
        self.assertEqual(e.observations()[-4:], [0, 0, 1, 0])
        e.apply_outputs([0, 1, 0, 0, 1, -1])
        e.apply_outputs([0, 1, 0, 0, 1, 1])
        self.assertEqual(e.memory, [0, -1])
        self.assertEqual(self.episode().memory, [])

    def test_movement_sensors_collision_and_rewards(self):
        e = self.episode()
        self.assertEqual(len(e.sensors()), 8)
        self.assertAlmostEqual(e.step('forward'), .45)
        self.assertAlmostEqual(e.step('backward'), -.1)
        self.assertAlmostEqual(e.step('backward'), -.05)
        self.assertEqual((e.x, e.y), (2, 1))
        self.assertAlmostEqual(e.step('forward'), .45)
        self.assertGreater(e.step('forward'), 100)
        self.assertTrue(e.escaped)
        e = self.episode()
        self.assertEqual(e.step('left'), -5)
        self.assertEqual((e.x, e.y), (1, 1))
        with self.assertRaises(ValueError):
            e.step('idle')

    def test_observation_does_not_include_path_or_reward(self):
        e = self.episode()
        before = e.observations()
        e.reward_path = []
        e.score = 10000
        self.assertEqual(e.observations(), before)

    def test_checkpoint_and_rollout(self):
        with tempfile.TemporaryDirectory() as d:
            model = Path(d) / 'memory.json'
            t = Trainer(Config(learned_memory=True, start_in_field=False,
                               rules=Rules(memory_steps=2)), model)
            self.assertEqual(t.network.architecture, (12, 12, 8, 6))
            t.network.save(model)
            loaded = Trainer.load(model)
            e = loaded.rollout(loaded.maze(0), loaded.network.weights, record=True)
            self.assertEqual(len(e.sensors()), 8)
            self.assertTrue(loaded.payload()['learned_memory'])


if __name__ == '__main__':
    unittest.main()

class UntilFailureTests(unittest.TestCase):
    def test_passes_old_limit_and_exits(self):
        e = MemoryEpisode(Maze('corridor', ('########', '#......E', '########'), (1,1)),
                          Rules(max_steps=2, until_failure=True))
        for _ in range(3):
            e.step('forward')
        self.assertFalse(e.done)
        for _ in range(3):
            e.step('forward')
        self.assertTrue(e.escaped)

    def test_wall_ends_immediately(self):
        e = MemoryEpisode(Maze('corridor', ('#####', '#...E', '#####'), (1,1)),
                          Rules(until_failure=True))
        e.step('left')
        self.assertTrue(e.done)
        self.assertFalse(e.escaped)

    def test_exact_cycle_ends_but_new_memory_does_not(self):
        maze = Maze('corridor', ('######', '#....E', '######'), (1,1))
        e = MemoryEpisode(maze, Rules(until_failure=True))
        e.step('forward')
        e.step('backward')
        e.step('backward')
        self.assertTrue(e.done)
        self.assertIn('løkke', e.event)
        e = MemoryEpisode(maze, Rules(until_failure=True))
        e.step('forward')
        e.step('backward')
        e.memory.append(1)
        e.step('backward')
        self.assertFalse(e.done)
