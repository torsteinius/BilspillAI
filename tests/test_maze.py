import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from games.maze.generator import generate, generate_field, next_size, shortest_path
from games.maze.training import Config, Trainer
from games.maze.world import Episode, Maze, Rules, compress_actions, decode_outputs


class MazeTests(unittest.TestCase):
    def simple(self):
        return Maze('straight', ('#####', '#...#', '#...E', '#...#', '#####'), (1,2))

    def test_random_mazes_are_reproducible_reachable_and_varied(self):
        layouts = set()
        for width,height in ((5,5),(8,8),(12,12),(18,18),(5,8),(8,5)):
            for seed in range(15):
                maze = generate(width,height,seed=seed)
                self.assertEqual(maze, generate(width,height,seed=seed))
                self.assertEqual((maze.width,maze.height),(width,height))
                route = shortest_path(maze)
                self.assertEqual(maze.cell(*route[-1]), 'E')
                self.assertTrue(all(maze.cell(*p) != '#' for p in route))
                layouts.add(maze.rows)
        self.assertGreater(len(layouts), 20)

    def test_size_grows_fifty_percent_in_both_dimensions(self):
        self.assertEqual(next_size(5,5),(8,8))
        self.assertEqual(next_size(8,8),(12,12))
        self.assertEqual(next_size(12,8),(18,12))

    def test_long_front_sensor_sees_through_exit_but_not_wall(self):
        maze = self.simple()
        self.assertEqual(maze.ray(1,2,0,0), maze.sensor_range)
        self.assertGreater(maze.sensor_range, math.hypot(maze.width,maze.height))
        self.assertEqual(maze.ray(1,2,2,0), .5)
        self.assertEqual(maze.ray(1,2,3,0), 1.5)

    def test_corner_blocks_diagonal_ray(self):
        maze=Maze('corner',('#####','#.#.#','#...E','#...#','#####'),(1,1))
        self.assertAlmostEqual(maze.ray(1,1,0,45),math.sqrt(.5))

    def test_turns_stay_in_place_and_forward_moves(self):
        e=Episode(self.simple())
        e.step('left')
        self.assertEqual((e.x,e.y,e.heading),(1,2,3))
        e.step('right');e.step('forward')
        self.assertEqual((e.x,e.y,e.heading),(2,2,0))
        self.assertEqual(e.last_reward,e.rules.forward_reward)

    def test_collision_stops_at_wall_and_exit_is_rewarded(self):
        e=Episode(self.simple());e.step('left');e.step('forward');e.step('forward')
        self.assertFalse(e.done);self.assertFalse(e.escaped)
        self.assertEqual((e.x,e.y),(1,1))
        self.assertEqual(e.last_reward,-e.rules.wall_penalty)
        e.step('right'); e.step('forward')
        self.assertEqual((e.x,e.y),(2,1))
        self.assertFalse(e.done)
        e=Episode(self.simple())
        for _ in range(3):e.step('forward')
        self.assertTrue(e.escaped)
        self.assertEqual(e.last_reward,e.rules.forward_reward+e.rules.exit_reward)
        with self.assertRaises(ValueError):e.step('forward')

    def test_revisit_penalty_uses_all_visits_and_resets(self):
        e=Episode(self.simple(),Rules(memory_steps=2))
        e.step('forward');e.step('left');e.step('left');e.step('forward')
        self.assertEqual(e.last_reward,e.rules.forward_reward-e.rules.revisit_penalty)
        self.assertEqual(e.visits[(1,2)],2)
        self.assertEqual(Episode(self.simple()).visits[(1,2)],1)

    def test_compression_fifty_forward_steps_uses_two_values(self):
        e=Episode(self.simple())
        e.actions=['forward']*50
        self.assertEqual(compress_actions(e.actions),[('forward',50)])
        obs=e.observations()
        self.assertEqual(len(obs),107)
        self.assertEqual(obs[7:9],[1/4,1.])
        self.assertEqual(obs[9:],[0.]*98)

    def test_window_is_trimmed_before_compression_and_retains_order(self):
        self.assertEqual(compress_actions(['forward']*60+['right']*3), [('forward',47),('right',3)])
        self.assertEqual(compress_actions(['forward','left','forward']),[('forward',1),('left',1),('forward',1)])
        actions=['left','right']*25
        self.assertEqual(len(compress_actions(actions)),50)
        e=Episode(self.simple());e.actions=actions
        self.assertEqual(len(e.observations()),107)
        self.assertTrue(all(0<=v<=1 for v in e.observations()))

    def test_turning_forever_times_out_and_memory_resets(self):
        e=Episode(self.simple(),Rules(max_steps=60))
        for _ in range(60):e.step('left')
        self.assertTrue(e.done);self.assertEqual(e.snapshot()['memory'],[('left',50)])
        self.assertEqual(Episode(self.simple()).observations()[7:],[0.]*100)

    def test_training_checkpoint_resume_and_disjoint_validation(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, start_in_field=False, population=2,train_mazes=2,validation_mazes=2,check_every=1,
                                   hidden=[3],rules=Rules(max_steps=8)),Path(d)/'maze.json')
            train_names={trainer.maze(i).name for i in range(2)}
            validation_names={trainer.maze(i,True).name for i in range(2)}
            self.assertFalse(train_names & validation_names)
            trainer.run(1)
            loaded=Trainer.load(trainer.model)
            self.assertEqual(loaded.network.weights,trainer.network.weights)
            self.assertEqual(loaded.config.rules.memory_steps,50)
            self.assertEqual(loaded.check_index,1)
            self.assertFalse(validation_names & {loaded.maze(i,True).name for i in range(2)})
            loaded.run(1)
            self.assertEqual(loaded.network.generation,2)
            self.assertEqual(len(loaded.network.history),2)
            self.assertEqual(loaded.network.history[-1]['width'],5)

    def test_next_replay_changes_maze_without_changing_training_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            trainer = Trainer(Config(success_streak=10, start_in_field=False, hidden=[], rules=Rules(max_steps=4)), Path(d)/'maze.json')
            with self.assertRaises(ValueError):
                trainer.next_replay()
            trainer.replay()
            first = trainer.recording
            second = trainer.next_replay()
            self.assertNotEqual(first['maze']['name'], second['maze']['name'])
            self.assertNotEqual(first['maze']['rows'], second['maze']['rows'])
            self.assertEqual(second['id'], first['id']+1)
            self.assertEqual(second['frames'][0]['memory'], [])
            self.assertEqual(trainer.check_index, 0)
            self.assertEqual(trainer.streak, 0)
            self.assertEqual(trainer.evaluations, [])
            self.assertEqual(trainer.network.generation, 0)
            self.assertEqual((trainer.width, trainer.height), (5, 5))

    def test_growth_requires_ten_consecutive_successes_and_failure_resets(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, start_in_field=False, stages=2),Path(d)/'maze.json')
            for _ in range(9): trainer.count_result(True)
            self.assertFalse(trainer.grow_if_ready())
            trainer.count_result(False)
            self.assertEqual(trainer.streak,0)
            for _ in range(9): trainer.count_result(True)
            self.assertFalse(trainer.grow_if_ready())
            trainer.count_result(True)
            self.assertTrue(trainer.grow_if_ready())
            self.assertEqual((trainer.width,trainer.height),(8,8))
            self.assertEqual(trainer.streak,0)
            trainer._metadata();trainer.network.save(trainer.model)
            self.assertEqual(Trainer.load(trainer.model).width,8)
            self.assertTrue((Path(d)/'maze_5x5.json').exists())

    def test_new_weights_reset_consecutive_successes(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, start_in_field=False, ),Path(d)/'maze.json')
            for _ in range(9):trainer.count_result(True)
            trainer.network.weights[0] += .1
            trainer.count_result(True)
            self.assertEqual(trainer.streak,1)

    def test_random_stream_rejects_same_geometry_even_with_new_seed(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, start_in_field=False, ),Path(d)/'maze.json')
            first=generate(seed=1)
            different=next(generate(seed=i) for i in range(2,100) if generate(seed=i).rows != first.rows)
            with patch('games.maze.training.generate',side_effect=[first,first,first,different]):
                self.assertEqual(trainer.fresh_maze('replay').rows,first.rows)
                self.assertEqual(trainer.fresh_maze('replay').rows,different.rows)

    def test_training_sets_change_each_generation(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, start_in_field=False, population=2,train_mazes=2,validation_mazes=2,check_every=2,
                                   hidden=[3],rules=Rules(max_steps=2)),Path(d)/'maze.json')
            trainer.run(2)
            first,second=trainer.network.history
            self.assertTrue(set(first['mazes']).isdisjoint(second['mazes']))


class MovementAndSpeedTests(unittest.TestCase):
    def test_stationary_penalty_starts_on_fifth_action_in_either_direction(self):
        maze=generate(seed=42)
        for actions in (['left']*6, ['right']*6, ['left','right']*3):
            episode=Episode(maze)
            for index,action in enumerate(actions,1):
                reward=episode.step(action)
                self.assertAlmostEqual(reward,-.02-(1 if index>4 else 0))
                self.assertEqual(episode.stationary_steps,index)

    def test_moving_resets_stationary_counter(self):
        episode=Episode(Maze('open',('#####','#...#','#...E','#...#','#####'),(2,2)))
        for _ in range(5):episode.step('right')
        episode.step('forward')
        self.assertEqual(episode.stationary_steps,0)
        self.assertAlmostEqual(episode.step('left'),-.02)

    def test_wall_contact_allows_at_least_thirty_actions(self):
        episode=Episode(Maze('wall',('#####','#...#','#...E','#...#','#####'),(1,2),2))
        for _ in range(30):
            episode.step('forward')
            self.assertFalse(episode.done)
            self.assertEqual((episode.x,episode.y),(1,2))
        self.assertEqual(episode.steps,30)
        self.assertLessEqual(episode.last_reward,-episode.rules.wall_penalty)
        for _ in range(episode.rules.max_steps-30):episode.step('forward')
        self.assertTrue(episode.done)
        self.assertEqual(episode.event,'Steggrensen er nådd')

    def test_binary_outputs_reach_all_four_actions(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, start_in_field=False, hidden=[],rules=Rules(max_steps=1)),Path(d)/'m.json')
            for values,action in (((-1.,-1.),'idle'),((1.,-1.),'left'),((-1.,1.),'right'),((1.,1.),'forward')):
                self.assertEqual(decode_outputs(values),action)
                weights=[0.]*trainer.network.weight_count
                for index,value in enumerate(values):
                    weights[(index+1)*(trainer.config.rules.input_count+1)-1]=value
                episode=trainer.rollout(generate(seed=42),weights)
                self.assertEqual(episode.last_action,action)
            self.assertEqual(trainer.network.architecture[-1],2)
            self.assertEqual(decode_outputs([0.,0.]),'idle')
            self.assertEqual(decode_outputs([0.,.01]),'right')

    def test_idle_stays_in_place_and_is_penalized_after_four(self):
        episode=Episode(generate(seed=42))
        pose=(episode.x,episode.y,episode.heading)
        for i in range(1,7):
            self.assertEqual(episode.step('idle'),0 if i<=4 else -1)
            self.assertEqual((episode.x,episode.y,episode.heading),pose)
        self.assertEqual(episode.snapshot()['memory'],[('idle',6)])

    def test_ten_unrecorded_attempts_then_one_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, start_in_field=False, ),Path(d)/'m.json')
            trainer.training_set=[generate(seed=i) for i in range(22)]
            with patch.object(trainer,'rollout',return_value=type('Result',(),{'score':3.})()) as rollout:
                self.assertEqual(trainer.evaluate(trainer.network.weights),3.)
            self.assertEqual([i for i,call in enumerate(rollout.call_args_list,1) if call.kwargs['record']],[11,22])


if __name__=='__main__':unittest.main()


class FieldTrainingTests(unittest.TestCase):
    def test_random_fields_have_free_centre_few_stones_and_reachable_edge(self):
        layouts=set()
        for seed in range(30):
            field=generate_field(seed=seed)
            self.assertEqual(field,generate_field(seed=seed))
            self.assertEqual(field.start,(15,15))
            self.assertEqual(field.cell(15,15),'.')
            self.assertEqual((field.width,field.height),(30,30))
            self.assertEqual(sum(row.count('#') for row in field.rows),50)
            self.assertEqual(field.kind,'field')
            self.assertEqual(field.cell(*shortest_path(field)[-1]),'E')
            self.assertTrue(all(cell=='E' for cell in field.rows[0]+field.rows[-1]))
            layouts.add(field.rows)
        self.assertGreater(len(layouts),20)

    def test_any_edge_is_success_and_stones_block(self):
        rows=('EEEEE','E...E','E.#.E','E...E','EEEEE')
        for start,heading in (((1,1),2),((3,1),0),((1,1),3),((1,3),1)):
            episode=Episode(Maze('field',rows,start,heading,kind='field'))
            episode.step('forward')
            self.assertTrue(episode.escaped)
            self.assertEqual(episode.last_reward,101)
        episode=Episode(Maze('stone',rows,(1,2),0,kind='field'))
        self.assertEqual(episode.sensors()[3],.5)
        episode.step('forward')
        self.assertFalse(episode.done)
        self.assertEqual((episode.x,episode.y),(1,2))
        self.assertEqual(episode.last_reward,-5)

    def test_field_advances_to_first_maze_without_reinitializing_weights(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(success_streak=10, ),Path(d)/'model.json')
            self.assertEqual(trainer.stage,-1)
            self.assertEqual(trainer.fresh_maze('training').kind,'field')
            trainer.network.weights[0]=.123
            for _ in range(9):trainer.count_result(True)
            self.assertFalse(trainer.grow_if_ready())
            trainer.count_result(True)
            self.assertTrue(trainer.grow_if_ready())
            self.assertEqual((trainer.stage,trainer.width,trainer.height),(-1,30,30))
            self.assertEqual(trainer.field_stones,75)
            trainer._metadata();trainer.network.save(trainer.model)
            self.assertEqual(Trainer.load(trainer.model).field_stones,75)
            for amount in (100,100):
                for _ in range(10):trainer.count_result(True)
                self.assertTrue(trainer.grow_if_ready())
                self.assertEqual(trainer.field_stones,amount)
            self.assertEqual((trainer.stage,trainer.width,trainer.height),(0,5,5))
            self.assertEqual(trainer.network.weights[0],.123)
            self.assertEqual(trainer.fresh_maze('training').kind,'maze')
            self.assertEqual(trainer.streak,0)
            self.assertTrue((Path(d)/'model_field_50.json').exists())
            trainer._metadata();trainer.network.save(trainer.model)
            self.assertEqual(Trainer.load(trainer.model).stage,0)


class CleanSuccessTests(unittest.TestCase):
    def test_exit_only_counts_if_collision_and_stall_free(self):
        maze=Maze('open',('#####','#...#','#...E','#...#','#####'),(1,2))
        good=Episode(maze)
        for _ in range(3):good.step('forward')
        self.assertTrue(good.clean_success)
        stalled=Episode(maze)
        for _ in range(5):stalled.step('idle')
        for _ in range(3):stalled.step('forward')
        self.assertTrue(stalled.escaped)
        self.assertFalse(stalled.clean_success)
        crashed=Episode(maze)
        for action in ['left','left','forward','left','left','forward','forward','forward']:crashed.step(action)
        self.assertTrue(crashed.escaped)
        self.assertEqual(crashed.collisions,1)
        self.assertFalse(crashed.clean_success)

    def test_default_requires_twenty_clean_successes(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(),Path(d)/'m.json')
            for _ in range(19):trainer.count_result(True)
            self.assertFalse(trainer.grow_if_ready())
            trainer.count_result(False)
            self.assertEqual(trainer.streak,0)
            for _ in range(20):trainer.count_result(True)
            self.assertTrue(trainer.grow_if_ready())


class PlannedGrowthTests(unittest.TestCase):
    def test_growth_waits_until_target_and_happens_once(self):
        with tempfile.TemporaryDirectory() as directory:
            trainer=Trainer(Config(start_in_field=False,stages=1),Path(directory)/'model.json')
            trainer.network.metadata['planned_growth']={'after_generation':500}
            trainer.network.weights[0]=.7
            trainer.network.generation=499
            self.assertFalse(trainer.apply_planned_growth())
            self.assertEqual(trainer.width,5)
            trainer.network.generation=500
            self.assertTrue(trainer.apply_planned_growth())
            self.assertEqual((trainer.width,trainer.height),(8,8))
            self.assertEqual(trainer.network.weights[0],.7)
            self.assertFalse(trainer.apply_planned_growth())
            loaded=Trainer.load(trainer.model)
            self.assertEqual(loaded.width,8)
            self.assertFalse(loaded.apply_planned_growth())
            self.assertTrue((Path(directory)/'model_before_growth.json').exists())
