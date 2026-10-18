import tempfile
import unittest
from pathlib import Path
from ai.network import NeuralNetwork
from ai_service.generic import GenericAPI


class MemoryFreezeTests(unittest.TestCase):
    def test_freeze_activation_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            model = NeuralNetwork([3, 2, 1])
            model.metadata['mutation_active_inputs'] = [True, False, False]
            model.save(home / 'source.json')
            api = GenericAPI(home)
            api.clone_legacy('masked', str(home / 'source.json'))
            settings = dict(network_id='masked', population_size=3, elite_count=1, mutation_sigma=.12, seed=42)
            sid = api.create_session(settings)['session_id']
            first = api.ask(sid, {'request_id':'a1'})
            _, data = api._session(sid)
            for candidate in data['candidates']:
                for index in (1,2,5,6):
                    self.assertEqual(candidate[index], 0.)
            self.assertNotEqual(data['candidates'][1][0], 0.)
            self.assertNotEqual(data['candidates'][1][3], 0.)  # Bias still mutates.
            self.assertNotEqual(data['candidates'][1][8], 0.)  # Hidden connections still mutate.
            body = dict(generation_id=first['generation_id'], fitness=[0,1,2], request_id='t1')
            with self.assertRaises(ValueError):
                api.tell(sid, dict(body, used_inputs=[True, 1, False]))
            # Occupied input may be zero: explicit occupancy activates it regardless.
            api.candidate_predict(sid, dict(generation_id=first['generation_id'], items=[dict(candidate_id='candidate-0', input=[0.,0.,0.])]))
            result = api.tell(sid, dict(body, used_inputs=[True, True, False]))
            self.assertEqual(result, api.tell(sid, dict(body, used_inputs=[True,True,False])))
            restored = GenericAPI(home)
            restored.ask(sid, {'request_id':'a2'})
            _, data = restored._session(sid)
            self.assertEqual(data['mutation_active_inputs'], [True,True,False])
            self.assertNotEqual(data['candidates'][1][1], 0.)
            self.assertEqual(data['candidates'][1][2], 0.)
            self.assertEqual(data['candidates'][1][6], 0.)
            new_sid = restored.create_session(settings)['session_id']
            self.assertEqual(restored._session(new_sid)[1]['mutation_active_inputs'], [True,True,False])


class MutationRandomnessTests(unittest.TestCase):
    def test_generation_varies_but_restart_reproduces_candidates(self):
        from ai_service.generic import EvolutionSession
        settings = dict(population_size=3, elite_count=1, mutation_sigma=.12, seed=42)
        live = EvolutionSession([0.] * 12, **settings)
        first = live.ask()
        self.assertEqual(first, live.ask())
        live.tell([1,0,0])  # Retain identical champion to isolate mutation changes.
        second = live.ask()
        self.assertNotEqual(first[1:], second[1:])
        restored = EvolutionSession([0.] * 12, generation=1, **settings)
        self.assertEqual(second, restored.ask())

    def test_new_api_session_continues_mutation_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            net = NeuralNetwork([2,2,1]); net.save(home/'source.json')
            api = GenericAPI(home); api.clone_legacy('test',str(home/'source.json'))
            settings = dict(network_id='test',population_size=3,elite_count=1,mutation_sigma=.12,seed=42)
            sid = api.create_session(settings)['session_id']
            asked = api.ask(sid,{'request_id':'a'})
            first = api._session(sid)[1]['candidates']
            api.tell(sid,dict(generation_id=asked['generation_id'],fitness=[1,0,0],request_id='t'))
            api.ask(sid,{'request_id':'b'})
            second = api._session(sid)[1]['candidates']
            new_sid = api.create_session(settings)['session_id']
            api.ask(new_sid,{'request_id':'a'})
            self.assertNotEqual(first,second)
            self.assertEqual(second,api._session(new_sid)[1]['candidates'])
