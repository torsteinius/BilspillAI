import unittest
from games.maze.history import HistoryEpisode,CHOICE_BITS
from games.maze.world import Maze,Rules
from scripts.train_exploration import freeze_unused

class ExplorationRewardTests(unittest.TestCase):
    def episode(self):
        maze=Maze('corridor',('#######','#.....E','#######'),(1,1),0)
        rules=Rules(until_failure=False,max_steps=8,movement_reward=.1,exploration_reward=1.,
            revisit_penalty=.2,wall_penalty=5.,stationary_penalty=5.,penalize_stationary_immediately=True,
            progress_reward=0.,path_reward=0.,landmark_reward=0.,backtrack_penalty=0.,exit_reward=100.)
        return HistoryEpisode(maze,rules,sensor_count=4,output_encoding='bits2',action_memory_steps=128)
    def test_new_cells_rewarded_once_and_back_and_forth_loses_points(self):
        e=self.episode()
        self.assertAlmostEqual(e.apply_outputs(CHOICE_BITS['forward']),1.1)
        self.assertAlmostEqual(e.apply_outputs(CHOICE_BITS['backward']),-.1)
        self.assertAlmostEqual(e.apply_outputs(CHOICE_BITS['backward']),-.1)
        self.assertAlmostEqual(e.score,.9)
    def test_wall_and_no_movement_are_hard_penalties_and_allow_recovery(self):
        e=self.episode()
        self.assertEqual(e.apply_outputs(CHOICE_BITS['left']),-10.)
        self.assertFalse(e.done)
        self.assertEqual(e.snapshot()['stall_penalties'],1)
        self.assertAlmostEqual(e.apply_outputs(CHOICE_BITS['right']),1.1)
        while not e.done:e.apply_outputs(CHOICE_BITS['left'])
        self.assertLessEqual(e.steps,8)
    def test_exit_keeps_large_bonus(self):
        e=self.episode()
        for _ in range(5):reward=e.apply_outputs(CHOICE_BITS['forward'])
        self.assertAlmostEqual(reward,101.1)
        self.assertTrue(e.escaped)
    def test_unused_columns_restored_but_used_weights_bias_and_hidden_stay(self):
        before=[.2]*12;candidate=[.9]*12
        freeze_unused(candidate,before,3,2,1)
        self.assertEqual(candidate,[.9,.2,.2,.9,.9,.2,.2,.9,.9,.9,.9,.9])
