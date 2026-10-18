import tempfile
from pathlib import Path
from unittest.mock import patch
import random
import unittest
from ai.network import NeuralNetwork
from games.maze.history import HistoryEpisode,architecture,widen_network,capacity
from games.maze.world import Rules, Maze
from games.maze.generator import generate
from games.maze.training import Trainer,Config


class YesDetector:
    def forward(self,_):return [1.]


class HistoryTests(unittest.TestCase):
    def test_deep_architecture_survives_growth_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "deep.json"
            t = Trainer(Config(deterministic_history=True, start_in_field=False, history_hidden_layers=23), p)
            t.streak = t.config.success_streak
            self.assertTrue(t.grow_if_ready())
            t._metadata(); t.network.save(p)
            restored = Trainer.load(p)
            expected = tuple(architecture(8, 8, 23))
            self.assertEqual(restored.network.architecture, expected)
            self.assertEqual(len(expected), 25)
            self.assertEqual(expected[0], 296)
            self.assertEqual(expected[-1], 4)
            gaps = [a-b for a,b in zip(expected, expected[1:])]
            self.assertLessEqual(max(gaps)-min(gaps), 1)

    def test_order_padding_unique_registration_and_reset(self):
        maze=Maze('corner',('#####','#...E','#.###','#.###','#####'),(1,1),0);rules=Rules(max_steps=8)
        e=HistoryEpisode(maze,rules)
        current=e.observations()[:8]
        self.assertEqual(e.observations()[8:],[0.]*72)
        with patch('games.maze.history.detector',return_value=YesDetector()):
            e.apply_outputs([1,0,0,0])
            self.assertEqual(list(e.memory[0]),current)
            self.assertEqual(e.observations()[8:16],current)
            self.assertEqual(e.observations()[:8],[v/maze.sensor_range for v in e.sensors()])
            if (e.x,e.y)==maze.start:
                e.apply_outputs([1,0,0,0]);self.assertEqual(len(e.memory),1)
        self.assertEqual(HistoryEpisode(maze,rules).memory,[])
        self.assertEqual(len(e.observations()),architecture(5,5)[0])

    def test_only_corners_and_junctions_enter_history_and_reward_once(self):
        maze = Maze('landmarks', ('#######','#.....E','#.#####','#...###','#######'), (1,2), 3)
        rules = Rules(progress_reward=0, path_reward=0, exploration_reward=0, backtrack_penalty=0,
                      revisit_penalty=0, max_steps=100)
        e = HistoryEpisode(maze, rules)
        self.assertIsNone(e.landmark_kind())
        self.assertEqual(e.apply_outputs([1,0,0,0]), 1.)  # Arrive at corner.
        self.assertEqual(e.memory, [])  # Straight departure was not recorded.
        self.assertEqual(e.landmark_kind(), 'corner')
        e.apply_outputs([0,0,1,0])  # Turn east and record the corner.
        self.assertEqual(len(e.memory), 1)
        self.assertIsNone(e.landmark_kind())
        self.assertEqual(e.apply_outputs([0,1,0,0]), 0.)  # Return: no second bonus.
        e.apply_outputs([0,1,0,0])
        self.assertEqual(len(e.memory), 1)
        e.x, e.y = 3, 3
        self.assertIsNone(e.landmark_kind())  # Dead end.
        junction = Maze('junction', ('#####','#...E','##.##','#####'), (2,1), 0)
        j = HistoryEpisode(junction, rules)
        self.assertEqual(j.landmark_kind(), 'junction')
        j.apply_outputs([1,0,0,0])
        self.assertEqual(len(j.memory), 1)

    def test_new_cells_rewarded_and_backtracking_never_farms_rewards(self):
        maze=Maze('branch',('#######','#.....E','###.###','###.###','#######'),(2,1),0)
        e=HistoryEpisode(maze,Rules(until_failure=False,max_steps=100,revisit_penalty=.05))
        self.assertAlmostEqual(e.step('forward'),1.45)  # New branch, path progress.
        self.assertAlmostEqual(e.step('right'),.15)  # New side corridor, away from exit.
        self.assertAlmostEqual(e.step('backward'),-.05)  # Old branch, toward exit, no bonus.
        self.assertEqual(e.event,'Gjenbesøk')
        self.assertAlmostEqual(e.step('backward'),-.10)  # Old side corridor, away from exit.
        self.assertAlmostEqual(e.step('backward'),-.05)
        self.assertAlmostEqual(e.step('right'),.45)  # Fresh cell with new distance record.

    def test_return_to_start_is_a_revisit(self):
        maze=Maze('corridor',('#######','#.....E','#######'),(1,1),0)
        e=HistoryEpisode(maze,Rules(until_failure=False,revisit_penalty=.05))
        self.assertAlmostEqual(e.step('forward'),.45)
        self.assertAlmostEqual(e.step('backward'),-.10)
        self.assertAlmostEqual(e.step('backward'),-.05)
        self.assertEqual(e.event,'Gjenbesøk')

    def test_widen_preserves_outputs(self):
        rng=random.Random(7);old=NeuralNetwork(architecture(5,5))
        old.weights=[rng.uniform(-.2,.2) for _ in old.weights]
        new=widen_network(old,architecture(8,8))
        x=[rng.random() for _ in range(old.architecture[0])]
        self.assertEqual(old.forward(x),new.forward(x+[0.]*(new.architecture[0]-len(x))))
        self.assertEqual(len(new.architecture),5)

    def test_growth_checkpoint_loads_correct_widths(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.json'
            t=Trainer(Config(deterministic_history=True,start_in_field=False),p)
            t.streak=t.config.success_streak
            self.assertTrue(t.grow_if_ready())
            t._metadata();t.network.save(p)
            restored=Trainer.load(p)
            self.assertEqual(restored.network.architecture,tuple(architecture(8,8)))
            self.assertTrue(restored.config.deterministic_history)
            e=restored.rollout(restored.maze(1),restored.network.weights)
            self.assertEqual(len(e.observations()),restored.network.architecture[0])

    def test_minimum_steps_keeps_wall_failures_running(self):
        maze=Maze('wall',('####','#..E','####'),(1,1),3)
        e=HistoryEpisode(maze,Rules(until_failure=True,min_steps=20))
        for _ in range(19):
            self.assertLess(e.step('forward'),0)
            self.assertFalse(e.done)
        e.step('forward')
        self.assertTrue(e.done)
        self.assertEqual(e.steps,20)

    def test_minimum_steps_keeps_loops_running_but_allows_exit(self):
        maze=Maze('corridor',('####','#..E','####'),(1,1),0)
        e=HistoryEpisode(maze,Rules(until_failure=True,min_steps=20))
        e.step('forward')
        for _ in range(18):
            e.step('backward')
            self.assertFalse(e.done)
        e.step('backward')
        self.assertTrue(e.done)
        self.assertFalse(e.escaped)
        e=HistoryEpisode(maze,Rules(until_failure=True,min_steps=20))
        e.step('forward');e.step('forward')
        self.assertTrue(e.escaped)
        self.assertEqual(e.steps,2)
