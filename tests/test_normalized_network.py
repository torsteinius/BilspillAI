import math
import random
import tempfile
import unittest
from pathlib import Path
from ai.network import NeuralNetwork
from ai_service.generic import GenericAPI


class NormalizedNetworkTests(unittest.TestCase):
    def test_manual_normalization_and_zero_input(self):
        net = NeuralNetwork([2,2,1])
        net.metadata['normalization'] = 'layernorm_hidden_v1'
        net.weights = [1.,0.,0., 0.,1.,0., 1.,-1.,0.]
        expected = math.tanh(2*math.tanh(1/math.sqrt(1+1e-5)))
        self.assertAlmostEqual(net.forward([3.,1.])[0], expected)
        self.assertEqual(net.forward([0.,0.]), [0.])

    def test_api_gpu_cpu_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory)
            net=NeuralNetwork([3,5,4,2]);rng=random.Random(9)
            net.weights=[rng.uniform(-1,1) for _ in net.weights]
            net.metadata['normalization']='layernorm_hidden_v1'
            net.save(home/'source.json')
            api=GenericAPI(home);api.clone_legacy('norm',str(home/'source.json'))
            inputs=[[0.,0.,0.],[.2,.8,-.1],[10.,-5.,4.]]
            outputs=api.predict('norm',{'inputs':inputs})['outputs']
            for x,y in zip(inputs,outputs):
                for expected,actual in zip(net.forward(x),y):self.assertAlmostEqual(expected,actual,places=5)
            sid=api.create_session(dict(network_id='norm',population_size=2,elite_count=1,seed=2))['session_id']
            asked=api.ask(sid,{'request_id':'a'})
            body=dict(generation_id=asked['generation_id'],items=[dict(candidate_id='candidate-0',sample_id=str(i),input=x) for i,x in enumerate(inputs)])
            answers=api.candidate_predict(sid,body)['items']
            self.assertEqual(answers,GenericAPI(home).candidate_predict(sid,body)['items'])
            for expected,answer in zip(outputs,answers):
                for a,b in zip(expected,answer['output']):self.assertAlmostEqual(a,b,places=5)
            # Normalization is per sample; adding other samples must not change it.
            for x,y in zip(inputs,outputs):
                alone=api.predict('norm',{'inputs':[x]})['outputs'][0]
                for a,b in zip(y,alone):self.assertAlmostEqual(a,b,places=5)
