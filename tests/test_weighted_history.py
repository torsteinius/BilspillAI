import tempfile
import unittest
from pathlib import Path

from games.maze.history import HistoryEpisode, VERSION_V2
from games.maze.training import Config, Trainer
from games.maze.world import Maze, Rules


class WeightedHistoryTests(unittest.TestCase):
    def episode(self):
        maze = Maze('corner', ('#######', '#.....E', '#.#####', '#...###', '#######'), (1, 2), 3)
        return HistoryEpisode(maze, Rules(max_steps=100), output_encoding='bits2',
            sensor_count=4, memory_decay=.75, memory_floor=.25, newest_first=True)

    def test_current_first_and_history_newest_first_with_floor(self):
        e = self.episode()
        rows = [tuple([i/10]*4) for i in range(1, 9)]
        e.memory = rows[:]
        inputs = e.observations()
        self.assertEqual(inputs[:4], [v/e.maze.sensor_range for v in e.sensors()])
        scales = [.75, .5625, .421875, .31640625, .25, .25, .25, .25]
        for i, (row, scale) in enumerate(zip(reversed(rows), scales)):
            self.assertEqual(inputs[4*(i+1):4*(i+2)], [v*scale for v in row])
        self.assertEqual(inputs[36:], [0.]*(len(inputs)-36))
        self.assertEqual(e.memory, rows)  # No repeated attenuation of stored values.
        self.assertEqual(e.observations(), inputs)
        frame = e.snapshot()
        self.assertEqual(frame['memory_scales'], scales)
        self.assertEqual([v for row in frame['memory'] for v in row], inputs[4:36])
        self.assertEqual(frame['sensor_angles'], [0, 90, 180, 270])

    def test_new_landmark_moves_previous_memory_back_one_group(self):
        e = self.episode()
        e.apply_outputs([1, 1])  # Arrive at first corner.
        self.assertEqual(len(e.memory), 0)
        first = tuple(e.observations()[:4])
        e.apply_outputs([-1, 1])  # Register corner then move east.
        self.assertEqual(e.observations()[4:8], [v*.75 for v in first])
        e.x, e.y, e.heading = 1, 3, 1  # Another real corner.
        second = tuple(e.observations()[:4])
        e.apply_outputs([1, -1])
        self.assertEqual(e.observations()[4:8], [v*.75 for v in second])
        self.assertEqual(e.observations()[8:12], [v*.5625 for v in first])

    def test_configuration_survives_save_reload_and_growth(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'model.json'
            config = Config(deterministic_history=True, start_in_field=False, history_hidden_layers=5,
                history_output_encoding='bits2', history_sensor_count=4,
                history_memory_decay=.75, history_memory_floor=.25, history_newest_first=True)
            t = Trainer(config, p)
            t.streak = config.success_streak
            self.assertTrue(t.grow_if_ready())
            t._metadata(); t.network.save(p)
            loaded = Trainer.load(p)
            self.assertEqual(loaded.network.metadata['observation_version'], VERSION_V2)
            self.assertEqual(loaded.network.architecture, (148, 124, 100, 75, 51, 27, 2))
            e = loaded.make_episode(loaded.maze(0))
            self.assertEqual(len(e.observations()), 148)
            self.assertEqual(len(e.sensors()), 4)
            self.assertEqual((e.memory_decay, e.memory_floor, e.newest_first), (.75, .25, True))


if __name__ == '__main__':
    unittest.main()
