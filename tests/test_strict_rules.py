"""Strict maze rules: walls and repeated states end the attempt at once."""
import unittest
from games.maze.history import HistoryEpisode
from games.maze.world import Maze, Rules

STRICT = dict(until_failure=True, min_steps=0, wall_penalty=2., revisit_penalty=.3)


class StrictRuleTests(unittest.TestCase):
    def test_first_wall_ends_attempt_with_small_penalty(self):
        maze = Maze('wall', ('####', '#..E', '####'), (1, 1), 3)
        e = HistoryEpisode(maze, Rules(**STRICT))
        self.assertEqual(e.step('forward'), -2.)
        self.assertTrue(e.done)
        self.assertEqual(e.steps, 1)

    def test_oscillating_backward_ends_on_first_repeat(self):
        maze = Maze('corridor', ('######', '#....E', '######'), (2, 1), 0)
        e = HistoryEpisode(maze, Rules(**STRICT))
        first = e.step('backward')       # new square west
        self.assertFalse(e.done)
        second = e.step('backward')      # back to start, same pose as at the start
        self.assertTrue(e.done)
        self.assertFalse(e.escaped)
        self.assertAlmostEqual(first, .2 - .05)
        self.assertAlmostEqual(second, -.3 - 2.)

    def test_oscillation_scores_worse_than_one_new_square(self):
        maze = Maze('corridor', ('######', '#....E', '######'), (2, 1), 0)
        swing = HistoryEpisode(maze, Rules(**STRICT))
        swing.step('backward'); swing.step('backward')
        explore = HistoryEpisode(maze, Rules(**STRICT))
        explore.step('forward')
        self.assertLess(swing.score, explore.score)

    def test_revisit_costs_more_than_new_square_earns(self):
        maze = Maze('corridor', ('#######', '#.....E', '#######'), (3, 1), 2)
        e = HistoryEpisode(maze, Rules(**STRICT))
        e.step('forward')                # west, new square
        e.step('backward')               # east, back to start: revisit
        self.assertLess(e.last_reward + .2, 0)


if __name__ == '__main__':
    unittest.main()
