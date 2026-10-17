import tempfile
from pathlib import Path
import unittest
from games.maze.remote_ai_app import LocalRunner
from games.maze.training import Trainer, Config
from games.maze.world import Rules

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
            self.assertEqual(trainer.network.weights,before)
            self.assertFalse((Path(d)/'unused.json').exists())
    def test_gpu_required(self):
        with tempfile.TemporaryDirectory() as d:
            trainer=Trainer(Config(deterministic_history=True,start_in_field=False),Path(d)/'unused.json')
            client=FakeClient(trainer.network.architecture)
            client.engine_status=lambda:dict(backend='python',metal_available=False)
            runner=LocalRunner(client,trainer,'test',1,2,2)
            runner.run()
            self.assertEqual(runner.payload()['phase'],'error')
            self.assertIsNone(client.scores)
