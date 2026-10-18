import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from games.maze.remote_ai_app import LocalRunner
from games.maze.training import Trainer, Config
from games.maze.world import Rules, Maze

class FakeClient:
    def __init__(self, architecture): self.architecture=architecture; self.scores=None
    def engine_status(self): return dict(backend='mlx-gpu',metal_available=True)
    def _request(self,*args): return {'metadata':{'architecture':list(self.architecture)}}
    def create_evolution_session(self,**kwargs):return {'session_id':'test'}
    def ask(self,*args):return dict(generation_id='g1',candidate_ids=['a','b'])
    def candidate_predict(self,sid,gid,items):
        # Return in a different order: the client must match IDs, not list positions.
        return dict(backend='mlx-gpu',timing_ms={},items=[dict(candidate_id=i['candidate_id'],sample_id=i['sample_id'],output=[1,0,0,0]) for i in reversed(items)])
    def tell(self,sid,gid,scores,*args):
        self.scores=scores
        return dict(selected_candidate='a',score=scores[0],checkpoint_id='new')

class RemoteAITests(unittest.TestCase):
    def test_four_sensor_training_unlocks_only_used_input_groups(self):
        class FourSensorClient(FakeClient):
            def candidate_predict(self, sid, gid, items):
                assert all(len(i['input']) == self.architecture[0] for i in items)
                return dict(backend='mlx-gpu',timing_ms={},items=[dict(candidate_id=i['candidate_id'],sample_id=i['sample_id'],output=[1,1]) for i in items])
            def tell(self, sid, gid, scores, *args, used_inputs=None):
                self.used_inputs=used_inputs
                return super().tell(sid,gid,scores,*args)
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(deterministic_history=True,start_in_field=False,
                history_sensor_count=4,history_memory_decay=.75,history_memory_floor=.25,
                history_newest_first=True,history_output_encoding='bits2'),Path(d)/'unused.json')
            trainer.network.metadata['mutation_active_inputs']=[i<4 for i in range(trainer.network.architecture[0])]
            maze=Maze('corner',('#####','#...E','#.###','#.###','#####'),(1,1),0)
            client=FourSensorClient(trainer.network.architecture)
            runner=LocalRunner(client,trainer,'test',1,2,2,record_frames=False)
            with patch.object(trainer,'fresh_maze',return_value=maze):
                runner.run()
            self.assertEqual(runner.payload()['phase'],'replay')
            self.assertEqual(client.used_inputs,[i<8 for i in range(trainer.network.architecture[0])])

    def test_headless_training_does_not_capture_frames(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(deterministic_history=True,start_in_field=False,rules=Rules(until_failure=True,min_steps=0)),Path(d)/'unused.json')
            runner=LocalRunner(FakeClient(trainer.network.architecture),trainer,'test',2,2,2,record_frames=False)
            with patch('games.maze.history.HistoryEpisode.snapshot',side_effect=AssertionError('Headless run captured a frame')):
                runner.run()
            state=runner.payload()
            self.assertEqual(state['phase'],'replay')
            self.assertEqual(state['attempts_evaluated'],8)
            self.assertIsNone(state['recording'])
            self.assertEqual(state['recordings'],[])
            self.assertEqual(runner.attempts,[])
            self.assertGreater(sum(state['action_counts'].values()),0)

    def test_local_simulation_and_fitness_submission(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(deterministic_history=True,start_in_field=False,rules=Rules(until_failure=True,min_steps=20)),Path(d)/'unused.json')
            before=trainer.network.weights[:]
            client=FakeClient(trainer.network.architecture)
            runner=LocalRunner(client,trainer,'test',1,2,2)
            runner.run()
            state=runner.payload()
            self.assertEqual(state['phase'],'replay')
            self.assertEqual(len(client.scores),2)
            self.assertIsNotNone(state['recording'])
            self.assertEqual(len(state['recordings']), 2)
            self.assertNotEqual(state['recordings'][0]['id'], state['recordings'][1]['id'])
            self.assertTrue(all(r['checkpoint_id'] == state['checkpoint_id'] for r in state['recordings']))
            self.assertAlmostEqual(sum(r['score'] for r in state['recordings'])/2, state['score'])
            self.assertEqual(trainer.network.weights,before)
            self.assertFalse((Path(d)/'unused.json').exists())
    def test_all_attempts_are_kept_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(deterministic_history=True,start_in_field=False,rules=Rules(until_failure=True,min_steps=20)),Path(d)/'unused.json')
            runner=LocalRunner(FakeClient(trainer.network.architecture),trainer,'test',2,2,2,record_all=True)
            runner.run()
            self.assertEqual(runner.payload()['attempt_count'],8)
            records=[runner.attempt(i) for i in range(8)]
            self.assertEqual([(r['generation'],r['candidate'],r['maze_index']) for r in records],
                             [(g,c,m) for g in (1,2) for c in (0,1) for m in (0,1)])
            self.assertEqual(len({r['id'] for r in records}),8)
            self.assertTrue(all(r['frames'][-1]['done'] for r in records))
            self.assertEqual([r['selected'] for r in records],[True,True,False,False]*2)
            records[0]['frames'].clear()
            self.assertTrue(runner.attempt(0)['frames'])
            with self.assertRaises(IndexError):runner.attempt(-1)

    def test_gpu_required(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(deterministic_history=True,start_in_field=False),Path(d)/'unused.json')
            client=FakeClient(trainer.network.architecture)
            client.engine_status=lambda:dict(backend='python',metal_available=False)
            runner=LocalRunner(client,trainer,'test',1,2,2)
            runner.run()
            self.assertEqual(runner.payload()['phase'],'error')
            self.assertIsNone(client.scores)
