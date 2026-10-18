import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai.network import NeuralNetwork
from ai_service.client import Client
from ai_service.generic import GenericAPI
from ai_service.server import handler
from games.maze.remote_ai_app import LocalRunner
from games.maze.training import Config, Trainer
from games.maze.world import Maze, Rules


class RemoteCurriculumTests(unittest.TestCase):
    def run_curriculum(self, failure=False):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            trainer = Trainer(Config(deterministic_history=True, start_in_field=False,
                history_sensor_count=4, history_output_encoding='bits2', check_every=2,
                success_streak=20, validation_mazes=20,
                rules=Rules(until_failure=True, min_steps=0)), home/'model.json')
            trainer.network.metadata['normalization'] = 'layernorm_hidden_v1'
            trainer.network.metadata['mutation_active_inputs'] = [i < 4 for i in range(trainer.network.architecture[0])]
            # A known policy: output 11, always forward. No random mutations in this fixture.
            stride = trainer.network.architecture[-2] + 1
            trainer.network.weights[-1] = 1.
            trainer.network.weights[-1-stride] = 1.
            trainer.network.save(trainer.model)
            old_arch = trainer.network.architecture
            old_output = trainer.network.forward([.3]*old_arch[0])
            api = GenericAPI(home)
            api.clone_legacy('test', trainer.model)
            server = ThreadingHTTPServer(('127.0.0.1',0), handler(SimpleNamespace(generic=api)))
            thread = threading.Thread(target=server.serve_forever); thread.start()
            client = Client(f'http://127.0.0.1:{server.server_port}')
            validations = []
            def maze(stream):
                width, height = trainer.width, trainer.height
                # Training always succeeds. Only held-out validation can block promotion.
                blocked = stream == 'validation' and failure and len(validations) == 9
                row = '#' + '.'*(width-2) + 'E'
                result = Maze(f'{stream}-{len(validations)}', tuple(['#'*width,row]+['#'*width]*(height-2)),(1,1),2 if blocked else 0)
                if stream == 'validation': validations.append(result)
                return result
            try:
                runner = LocalRunner(client, trainer, 'test', 3, 1, 2, record_frames=False)
                with patch.object(trainer, 'fresh_maze', side_effect=maze): runner.run()
                self.assertEqual(runner.payload()['phase'],'replay',runner.payload().get('error'))
                self.assertEqual(len(validations),20)
                saved = client.checkpoint('test')['checkpoint']
                self.assertEqual(saved['generation'],3)
                if failure:
                    self.assertEqual(trainer.width,5)
                    self.assertEqual(saved['architecture'],list(old_arch))
                    self.assertEqual(runner.payload()['validation_success'],.95)
                else:
                    self.assertEqual((trainer.width,trainer.height),(8,8))
                    self.assertEqual(saved['architecture'],[148,*old_arch[1:]])
                    self.assertEqual(saved['mutation_active_inputs'][old_arch[0]:],[False]*(148-old_arch[0]))
                    restored = Trainer.load(trainer.model)
                    self.assertEqual(restored.network.architecture,tuple(saved['architecture']))
                    self.assertEqual(restored.network.forward([.3]*old_arch[0]+[0.]*(148-old_arch[0])),old_output)
                    self.assertEqual(len(restored.make_episode(restored.maze(1)).observations()),148)
            finally:
                client.close(); server.shutdown(); server.server_close(); thread.join()

    def test_success_on_twenty_fresh_mazes_grows_and_training_continues(self):
        self.run_curriculum()

    def test_one_failed_validation_blocks_growth_despite_perfect_training(self):
        self.run_curriculum(failure=True)

    def test_normalized_growth_preserves_trained_function_and_freezes_added_memory(self):
        import random
        with tempfile.TemporaryDirectory() as directory:
            trainer = Trainer(Config(deterministic_history=True,start_in_field=False,
                history_sensor_count=4,history_output_encoding='bits2'),Path(directory)/'model.json')
            rng=random.Random(19)
            trainer.network.weights=[rng.uniform(-.5,.5) for _ in trainer.network.weights]
            trainer.network.metadata.update(normalization='layernorm_hidden_v1',
                mutation_active_inputs=[True]*trainer.network.architecture[0])
            trainer.network.generation=7000
            inputs=[rng.uniform(-1,1) for _ in range(trainer.network.architecture[0])]
            expected=trainer.network.forward(inputs)
            trainer.streak=20
            self.assertTrue(trainer.grow_if_ready())
            inputs += [.8]*(trainer.network.architecture[0]-len(inputs))
            self.assertEqual(trainer.network.forward(inputs),expected)
            self.assertEqual(trainer.network.generation,7000)
            trainer._metadata();trainer.network.save(trainer.model)
            restored=Trainer.load(trainer.model)
            self.assertEqual(restored.network.forward(inputs),expected)

    def test_checkpoint_transition_rejects_stale_write_and_invalidates_sessions(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory); path=home/'network.json'
            network=NeuralNetwork([4,3,2]); network.save(path)
            api=GenericAPI(home); api.clone_legacy('test',path)
            exported=api.export_checkpoint('test')
            sid=api.create_session(dict(network_id='test',population_size=1,elite_count=1))['session_id']
            api.ask(sid,{'request_id':'first'})
            expanded=network.expand_inputs(4); expanded.save(path)
            body=dict(checkpoint=json.loads(path.read_text()),expected_checkpoint_id=exported['checkpoint_id'])
            api.replace_checkpoint('test',body)
            self.assertEqual(api.describe('test')['metadata']['architecture'],[8,3,2])
            with self.assertRaises(ValueError):api.replace_checkpoint('test',body)
            with self.assertRaises(LookupError):api.ask(sid,{'request_id':'stale'})
            # The archived pre-growth file is still available.
            self.assertEqual(NeuralNetwork.load(home/'generic-models/test/checkpoint.json').architecture,(4,3,2))
