import json
import random
import tempfile
import unittest
from pathlib import Path
from games.maze.history import HistoryEpisode, VERSION_V3
from games.maze.training import Config, Trainer
from games.maze.world import Maze, Rules
from scripts.add_route_choice_memory import migrate_model


class ChoiceMemoryTests(unittest.TestCase):
    def episode(self):
        maze=Maze('cross',('#######','###.###','#.....E','###.###','#######'),(3,2),0)
        return HistoryEpisode(maze,Rules(max_steps=100),sensor_count=4,output_encoding='bits2',
                              choice_memory=True,newest_first=True,memory_decay=.75,memory_floor=.25)

    def test_choice_is_visible_only_after_action_and_straight_corridor_adds_nothing(self):
        a,b=self.episode(),self.episode()
        self.assertEqual(a.observations(),b.observations())
        self.assertEqual(a.observations()[4:],[0.]*(len(a.observations())-4))
        sensors=a.observations()[:4]
        a.apply_outputs([1,1]); b.apply_outputs([-1,1])
        self.assertEqual(a.observations()[4:10],[x*.75 for x in sensors]+[.75,.75])
        self.assertEqual(b.observations()[8:10],[-.75,.75])
        a.apply_outputs([1,1])
        self.assertEqual(len(a.memory),1)

    def test_revisit_refreshes_view_and_choice_without_duplicating_place(self):
        a=self.episode();a.apply_outputs([1,1]);a.apply_outputs([-1,-1])
        before=a.observations()[:4]
        self.assertEqual(a.heading,2)
        a.apply_outputs([1,-1])
        self.assertEqual(len(a.memory),1)
        self.assertEqual(a.memory[0],tuple(before)+(1.,-1.))
        self.assertEqual(a.observations()[8:10],[.75,-.75])

    def test_migration_preserves_existing_function_and_loads_choice_format(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'old.json';out=Path(d)/'new.json'
            t=Trainer(Config(deterministic_history=True,start_in_field=False,history_sensor_count=4,
                             history_output_encoding='bits2'),p)
            rng=random.Random(3)
            t.network.weights=[rng.uniform(-.2,.2) for _ in t.network.weights];t.network.save(p)
            original=p.read_bytes();new=migrate_model(p,out)
            x=[rng.random() for _ in range(t.network.architecture[0])]
            expanded=x[:4]
            for i in range(4,len(x),4):expanded+=x[i:i+4]+[-1.,1.]
            self.assertEqual(t.network.forward(x),new.forward(expanded))
            loaded=Trainer.load(out)
            self.assertEqual(loaded.network.metadata['observation_version'],VERSION_V3)
            self.assertTrue(loaded.config.history_choice_memory)
            self.assertEqual(len(loaded.make_episode(loaded.maze(0)).observations()),new.architecture[0])
            self.assertEqual(p.read_bytes(),original)
