"""Small dependency-free client for another Mac (use through an SSH tunnel)."""
import json
from urllib.request import Request, urlopen

class Client:
    def __init__(self, base_url='http://127.0.0.1:8780'): self.base_url=base_url.rstrip('/')
    def _request(self, method, path, payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        with urlopen(Request(self.base_url+path, data=data, method=method, headers={'Content-Type':'application/json'})) as r: return json.load(r)
    def import_maze(self, network_id='maze-history-v1'): return self._request('POST','/networks',{'network_id':network_id})
    def train(self, generations, request_id, network_id='maze-history-v1'): return self._request('POST','/training-runs',{'network_id':network_id,'additional_generations':generations,'request_id':request_id})
    def status(self, run_id): return self._request('GET',f'/training-runs/{run_id}')
    def stop(self, run_id): return self._request('POST',f'/training-runs/{run_id}/stop',{})
    def recording(self, run_id): return self._request('GET',f'/training-runs/{run_id}/recording')
    def engine_status(self): return self._request('GET','/v1/status')
    def import_legacy(self, network_id, source_checkpoint, app_id='maze'): return self._request('POST','/v1/networks/import-legacy',{'network_id':network_id,'source_checkpoint':source_checkpoint,'app_id':app_id})
    def predict(self, network_id, inputs, request_id=None): return self._request('POST',f'/v1/networks/{network_id}/predict',{'inputs':inputs,'request_id':request_id})
    def create_evolution_session(self, **settings): return self._request('POST','/v1/evolution/sessions',settings)
    def ask(self, session_id, request_id): return self._request('POST',f'/v1/evolution/sessions/{session_id}/ask',{'request_id':request_id})
    def candidate_predict(self, session_id, generation_id, items): return self._request('POST',f'/v1/evolution/sessions/{session_id}/predict',{'generation_id':generation_id,'items':items})
    def tell(self, session_id, generation_id, fitness, request_id, evaluation_set_id='local-set'): return self._request('POST',f'/v1/evolution/sessions/{session_id}/tell',{'generation_id':generation_id,'fitness':fitness,'request_id':request_id,'evaluation_set_id':evaluation_set_id})
