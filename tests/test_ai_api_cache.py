import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ai.network import NeuralNetwork
from ai_service.generic import GenericAPI

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        model=NeuralNetwork([3,5,2])
        model.weights=[.03*(i%11-5) for i in range(len(model.weights))]
        self.source=self.home/'source.json';model.save(self.source)
        self.api=GenericAPI(self.home)
        self.api.clone_legacy('test',str(self.source))
        self.sid=self.api.create_session(dict(network_id='test',population_size=3,elite_count=1,mutation_sigma=.1,seed=7))['session_id']
        self.asked=self.api.ask(self.sid,{'request_id':'a1'})
        self.body=dict(generation_id=self.asked['generation_id'],items=[
            dict(candidate_id='candidate-2',sample_id='a',input=[.1,.2,.3]),
            dict(candidate_id='candidate-0',sample_id='b',input=[.5,.2,.1]),
            dict(candidate_id='candidate-2',sample_id='c',input=[.7,.3,.2])])
    def tearDown(self):self.tmp.cleanup()
    def test_warm_call_has_no_database_read_or_prepare_and_preserves_outputs(self):
        first=self.api.candidate_predict(self.sid,self.body)
        self.assertFalse(first['weights_cache_hit'])
        with patch.object(self.api,'connect',side_effect=AssertionError('Unexpected DB read')),patch.object(self.api.backend,'prepare',side_effect=AssertionError('Unexpected prepare')):
            second=self.api.candidate_predict(self.sid,self.body)
        self.assertTrue(second['weights_cache_hit']);self.assertTrue(second['session_cache_hit'])
        self.assertEqual(first['items'],second['items'])
        _,data=self.api._session(self.sid)
        for item,answer in zip(self.body['items'],second['items']):
            i=int(item['candidate_id'].split('-')[1]);net=NeuralNetwork(data['architecture'])
            expected=net.forward(item['input'],data['candidates'][i])
            for a,b in zip(expected,answer['output']):self.assertAlmostEqual(a,b,places=6)
    def test_tell_invalidates_old_generation_and_restart_recovers(self):
        self.api.candidate_predict(self.sid,self.body)
        result=self.api.tell(self.sid,dict(generation_id=self.asked['generation_id'],fitness=[1,2,3],request_id='t1'))
        self.assertEqual(result['selected_candidate'],'candidate-2')
        self.assertFalse(any(k[:2]==('session',self.sid) for k in self.api._prepared))
        with self.assertRaises(ValueError):self.api.candidate_predict(self.sid,self.body)
        asked=self.api.ask(self.sid,{'request_id':'a2'})
        self.body['generation_id']=asked['generation_id']
        current=self.api.candidate_predict(self.sid,self.body)
        restored=GenericAPI(self.home).candidate_predict(self.sid,self.body)
        self.assertEqual(current['items'],restored['items'])
    def test_model_cache_and_nonfinite_input(self):
        first=self.api.predict('test',{'inputs':[[.1,.2,.3]]})
        from ai_service.generic import DenseTanhCheckpoint
        with patch.object(DenseTanhCheckpoint,'load',side_effect=AssertionError('Reload')):
            second=self.api.predict('test',{'inputs':[[.1,.2,.3]]})
        self.assertEqual(first['outputs'],second['outputs'])
        self.body['items'][0]['input'][0]=float('nan')
        with self.assertRaises(ValueError):self.api.candidate_predict(self.sid,self.body)

if __name__=='__main__':unittest.main()

class HTTPReuseTests(unittest.TestCase):
    def test_client_reuses_connection_with_server(self):
        import threading
        from types import SimpleNamespace
        from http.server import ThreadingHTTPServer
        from ai_service.server import handler
        from ai_service.client import Client
        service=SimpleNamespace(generic=SimpleNamespace(status=lambda:{'backend':'test'}))
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(service))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        client=Client('http://127.0.0.1:'+str(server.server_port))
        try:
            self.assertEqual(client.engine_status()['backend'],'test')
            connection=client._connection.sock
            self.assertIsNotNone(connection)
            self.assertEqual(client.engine_status()['backend'],'test')
            self.assertIs(client._connection.sock,connection)
        finally:
            client.close();server.shutdown();server.server_close();thread.join()
