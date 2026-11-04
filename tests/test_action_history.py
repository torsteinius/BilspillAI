import tempfile
import unittest
from pathlib import Path
from games.maze.history import HistoryEpisode, CHOICE_BITS, VERSION_V4
from games.maze.training import Trainer,Config
from games.maze.world import Maze,Rules
from scripts.add_route_choice_memory import fresh_action_model


class ActionHistoryTests(unittest.TestCase):
    def test_every_step_remembers_only_previous_choices_and_caps_history(self):
        maze=Maze('straight',('#########','#.......E','#########'),(1,1),0)
        e=HistoryEpisode(maze,Rules(max_steps=100),sensor_count=4,output_encoding='bits2',
            action_memory_steps=2,newest_first=True,memory_decay=.75,memory_floor=.25)
        self.assertEqual(e.observations()[4:],[0.]*4)
        for action in ('forward','forward','backward'):
            e.apply_outputs(CHOICE_BITS[action])
        self.assertEqual(len(e.memory),2)
        self.assertEqual(e.observations()[4:],[-.75,-.75,.5625,.5625])
        self.assertFalse(e.registered)
        self.assertFalse(e.memory_places)
        self.assertTrue(all(len(row)==2 for row in e.memory))
        self.assertEqual(e.snapshot()['memory_row_width'],2)

    def test_random_initialization_does_not_inherit_learned_weights_or_state(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);p=d/'old.json'
            t=Trainer(Config(deterministic_history=True,start_in_field=False,history_sensor_count=4,
                history_output_encoding='bits2'),p)
            t.network.weights=[987.]*t.network.weight_count;t.network.generation=7400
            t.network.history=[{'generation':7400}];t.network.save(p)
            new=fresh_action_model(p,d/'fresh.json',seed=123,slots=8)
            again=fresh_action_model(p,d/'again.json',seed=123,slots=8)
            self.assertEqual(new.weights,again.weights)
            self.assertEqual(new.generation,0);self.assertEqual(new.history,[])
            self.assertNotIn(987.,new.weights);self.assertTrue(all(x!=0 for x in new.weights))
            loaded=Trainer.load(d/'fresh.json')
            self.assertEqual(loaded.network.metadata['observation_version'],VERSION_V4)
            self.assertEqual(len(loaded.make_episode(loaded.maze(0)).observations()),20)
            self.assertFalse(new.metadata['initialization']['transferred_weights'])
