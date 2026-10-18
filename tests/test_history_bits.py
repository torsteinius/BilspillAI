import math
from pathlib import Path
import tempfile
import unittest

from games.maze.history import HistoryEpisode, decode_bits
from games.maze.training import Config, Trainer
from games.maze.world import Maze, Rules


class HistoryBitTests(unittest.TestCase):
    def test_bits_drive_real_movement_and_recording(self):
        maze = Maze('open', ('#######', '#.....E', '#.....#', '#.....#', '#######'), (3, 2), 0)
        for values, action, position, heading, bits in [
            ([-.2, -.3], 'backward', (2, 2), 2, [0, 0]),
            ([-.2, .3], 'right', (3, 3), 1, [0, 1]),
            ([.2, -.3], 'left', (3, 1), 3, [1, 0]),
            ([.2, .3], 'forward', (4, 2), 0, [1, 1]),
            ([0., 0.], 'backward', (2, 2), 2, [0, 0]),
        ]:
            with self.subTest(values=values):
                episode = HistoryEpisode(maze, Rules(), output_encoding='bits2')
                episode.apply_outputs(values)
                frame = episode.snapshot()
                self.assertEqual((episode.x, episode.y), position)
                self.assertEqual(episode.heading, heading)
                self.assertEqual(frame['action'], action)
                self.assertEqual(frame['output_bits'], bits)
                self.assertEqual(frame['output_values'], values)

    def test_invalid_outputs_rejected(self):
        for values in ([0], [0, 0, 0, 0], [math.nan, 1], [1, math.inf]):
            with self.assertRaises(ValueError):
                decode_bits(values)

    def test_checkpoint_and_rollout_preserve_two_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bits.json'
            trainer = Trainer(Config(deterministic_history=True, start_in_field=False,
                history_hidden_layers=5, history_output_encoding='bits2',
                rules=Rules(max_steps=3)), path)
            trainer.network.weights[-1] = 1.  # 01: turn right each step.
            trainer.network.save(path)
            restored = Trainer.load(path)
            self.assertEqual(restored.network.architecture[-1], 2)
            self.assertEqual(len(restored.network.architecture), 7)
            episode = restored.rollout(restored.maze(0), restored.network.weights, record=True)
            self.assertEqual(episode.actions, ['right']*3)
            for frame in restored.recording['frames'][1:]:
                self.assertEqual(frame['output_bits'], [0, 1])
                self.assertEqual(frame['action'], 'right')
            restored.streak = restored.config.success_streak
            restored.grow_if_ready()
            self.assertEqual(restored.network.architecture[-1], 2)


if __name__ == '__main__':
    unittest.main()
