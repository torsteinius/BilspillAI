"""Generic API facade.  It deliberately has no dependency on games.*."""
import hashlib, json, shutil, sqlite3, time, uuid, sys
import threading
from collections import OrderedDict
from functools import wraps
from pathlib import Path
# Source checkouts have an ai_engine project directory which can shadow the
# installed package; put its package source first only for this local runner.
_ENGINE_SRC = Path(__file__).resolve().parents[1] / 'ai_engine' / 'src'
if str(_ENGINE_SRC) not in sys.path: sys.path.insert(0, str(_ENGINE_SRC))
from ai_engine import DenseTanhCheckpoint, MLXDenseBackend, EvolutionSession

def _hash(path):
    h=hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()
def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        started = time.perf_counter()
        with self._lock:
            acquired = time.perf_counter()
            try:
                result = method(self, *args, **kwargs)
            except Exception:
                # An interrupted write must not leave an uncommitted in-memory state.
                self._sessions.clear()
                self._prepared.clear()
                raise
            if isinstance(result, dict) and 'timing_ms' in result:
                result['timing_ms']['queue_wait'] = (acquired-started)*1000
                result['timing_ms']['total'] = (time.perf_counter()-started)*1000
            return result
    return call

class GenericAPI:
    def __init__(self, home):
        self._lock = threading.RLock()
        self._sessions = OrderedDict()
        self._prepared = OrderedDict()
        self.home=Path(home); self.db=self.home/'generic.sqlite3'; self.backend=MLXDenseBackend()
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS models (network_id TEXT PRIMARY KEY, app_id TEXT NOT NULL, checkpoint_id TEXT NOT NULL, checkpoint TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, network_id TEXT NOT NULL, data TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL);''')
    def _remember(self, cache, key, value, limit=4):
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > limit:
            cache.popitem(last=False)
        return value

    def _layers(self, key, architecture, populations):
        hit = key in self._prepared
        if hit:
            self._prepared.move_to_end(key)
        else:
            self._remember(self._prepared, key, self.backend.prepare(architecture, populations))
        return self._prepared[key], hit

    def connect(self):
        db=sqlite3.connect(self.db); db.row_factory=sqlite3.Row; return db
    def status(self): return {'backend':self.backend.name, 'metal_available':True, 'gpu_probe_synchronized_ms':self.backend.probe_ms, 'supported_network_types':['dense_tanh'], 'supported_training_methods':['evolution']}
    def model(self, network_id):
        with self.connect() as db: row=db.execute('SELECT * FROM models WHERE network_id=?',(network_id,)).fetchone()
        if not row: raise LookupError('Unknown network_id')
        return row
    @serialized
    def clone_legacy(self, network_id, source_path, app_id='maze'):
        if not isinstance(network_id,str) or not network_id: raise ValueError('network_id is required')
        source=Path(source_path); checkpoint=DenseTanhCheckpoint.load(source)
        target=self.home/'generic-models'/network_id; target.mkdir(parents=True,exist_ok=True)
        saved=target/'checkpoint.json'; shutil.copy2(source,saved); checkpoint_id=_hash(saved)
        metadata={'network_type':'dense_tanh','architecture':list(checkpoint.architecture),'dtype':'float32','input_schema':'application-defined vector','output_schema':'application-defined vector','training_methods':['evolution'],'source_sha256':_hash(source),'normalization':checkpoint.payload.get('normalization')}
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO models VALUES (?,?,?,?,?,?)',(network_id,app_id,checkpoint_id,str(saved),json.dumps(metadata),_now()))
        return self.describe(network_id)
    def describe(self, network_id):
        r=self.model(network_id); return {'network_id':r['network_id'],'app_id':r['app_id'],'checkpoint_id':r['checkpoint_id'],'metadata':json.loads(r['metadata'])}
    @serialized
    def export_checkpoint(self, network_id):
        model = self.model(network_id)
        return dict(checkpoint_id=model['checkpoint_id'],
                    checkpoint=json.loads(Path(model['checkpoint']).read_text()))

    @serialized
    def replace_checkpoint(self, network_id, body):
        """Replace at an application-owned curriculum boundary, retaining the old file."""
        model = self.model(network_id)
        if body.get('expected_checkpoint_id') != model['checkpoint_id']:
            raise ValueError('Checkpoint changed before replacement')
        checkpoint = DenseTanhCheckpoint(body['checkpoint'])
        old = DenseTanhCheckpoint.load(model['checkpoint'])
        if checkpoint.payload.get('generation') != old.payload.get('generation'):
            raise ValueError('Replacement must preserve generation')
        active = checkpoint.payload.get('mutation_active_inputs')
        if active is not None:
            self.active_inputs(active, checkpoint.architecture[0])
        target = Path(model['checkpoint']).with_name(f'checkpoint-transition-{uuid.uuid4().hex}.json')
        checkpoint.save(target)
        metadata = json.loads(model['metadata'])
        metadata.update(architecture=list(checkpoint.architecture), normalization=checkpoint.payload.get('normalization'))
        with self.connect() as db:
            db.execute('UPDATE models SET checkpoint=?,checkpoint_id=?,metadata=? WHERE network_id=?',
                       (str(target),_hash(target),json.dumps(metadata),network_id))
            # Old sessions use the old input shape and must never write over the transition.
            db.execute('DELETE FROM sessions WHERE network_id=?',(network_id,))
        self._sessions.clear()
        self._prepared.clear()
        return self.describe(network_id)

    @serialized
    def predict(self, network_id, body):
        started=time.perf_counter(); r=self.model(network_id); inputs=body.get('inputs')
        key=('model', network_id, r['checkpoint_id'])
        architecture=json.loads(r['metadata'])['architecture']
        hit=key in self._prepared
        if hit:
            self._prepared.move_to_end(key)
            layers=self._prepared[key]
        else:
            checkpoint=DenseTanhCheckpoint.load(r['checkpoint'])
            layers,_=self._layers(key,checkpoint.architecture,[checkpoint.weights])
        if not isinstance(inputs,list) or not inputs: raise ValueError('inputs must be a non-empty batch')
        if any(not isinstance(row,list) or len(row)!=architecture[0] or any(type(x) not in (int,float) or x!=x or abs(x)==float('inf') for x in row) for row in inputs): raise ValueError(f'each input must contain {architecture[0]} finite numbers')
        outputs, compute=self.backend.predict_prepared(layers,[inputs],normalization=json.loads(r['metadata']).get('normalization'))
        return {'network_id':network_id,'checkpoint_id':r['checkpoint_id'],'request_id':body.get('request_id'),'backend':self.backend.name,'outputs':outputs[0],'timing_ms':{'queue_wait':0,'model_compute_wall':compute,'total':(time.perf_counter()-started)*1000},'batch_size':len(inputs),'weights_cache_hit':hit}
    @staticmethod
    def active_inputs(value, width):
        if not isinstance(value, list) or len(value) != width or any(type(v) is not bool for v in value):
            raise ValueError('mutation_active_inputs must contain one boolean per input')
        return value[:]

    @staticmethod
    def mutation_mask(data):
        active = data.get('mutation_active_inputs')
        if active is None:
            return None
        width, neurons = data['architecture'][:2]
        first = (active + [True]) * neurons
        return first + [True] * (len(data['champion']) - len(first))

    @serialized
    def create_session(self, body):
        m=self.model(body.get('network_id')); size=body.get('population_size',36); elite=body.get('elite_count',6); sigma=body.get('mutation_sigma',.12); seed=body.get('seed',42)
        if not isinstance(size,int) or not isinstance(elite,int) or not isinstance(sigma,(int,float)) or not isinstance(seed,int): raise ValueError('invalid evolution session settings')
        c=DenseTanhCheckpoint.load(m['checkpoint']); session_id=str(uuid.uuid4()); data={'request_ids':{},'checkpoint':m['checkpoint'],'checkpoint_id':m['checkpoint_id'],'architecture':list(c.architecture),'champion':c.weights,'normalization':c.payload.get('normalization'),'population_size':size,'elite_count':elite,'mutation_sigma':sigma,'seed':seed,'generation':0,'mutation_generation_start':c.payload.get('generation',0),'candidates':None,'asked':None}
        if 'mutation_active_inputs' in c.payload:
            data['mutation_active_inputs'] = self.active_inputs(c.payload['mutation_active_inputs'], c.architecture[0])
        with self.connect() as db: db.execute('INSERT INTO sessions VALUES (?,?,?,?,?)',(session_id,m['network_id'],json.dumps(data),'active',_now()))
        return {'session_id':session_id,'network_id':m['network_id'],'checkpoint_id':m['checkpoint_id'],'settings':{'population_size':size,'elite_count':elite,'mutation_sigma':sigma,'seed':seed}}
    def _session(self, session_id):
        if session_id in self._sessions:
            self._sessions.move_to_end(session_id)
            return self._sessions[session_id]
        with self.connect() as db: r=db.execute('SELECT * FROM sessions WHERE session_id=?',(session_id,)).fetchone()
        if not r: raise LookupError('Unknown session_id')
        return self._remember(self._sessions,session_id,(r,json.loads(r['data'])))
    def _save(self, session_id,data):
        self._sessions.pop(session_id,None)
        for key in list(self._prepared):
            if key[:2] == ('session',session_id): self._prepared.pop(key)
        with self.connect() as db: db.execute('UPDATE sessions SET data=? WHERE session_id=?',(json.dumps(data),session_id))
    @serialized
    def ask(self, session_id, body):
        row,d=self._session(session_id); rid=body.get('request_id')
        if rid and rid in d['request_ids']: return d['request_ids'][rid]
        if d['asked']: return d['asked']
        e=EvolutionSession(d['champion'],population_size=d['population_size'],elite_count=d['elite_count'],mutation_sigma=d['mutation_sigma'],seed=d['seed'],generation=d['generation'] + d.get('mutation_generation_start',0),mutation_mask=self.mutation_mask(d)); candidates=e.ask(); d['candidates']=candidates; generation_id=f"generation-{d['generation']+1}"; d['asked']={'generation_id':generation_id,'champion_candidate_id':'candidate-0','candidate_ids':[f'candidate-{i}' for i in range(len(candidates))]}; d['request_ids'][rid]=d['asked']; self._save(session_id,d); return d['asked']
    @serialized
    def candidate_predict(self, session_id, body):
        started=time.perf_counter()
        session_hit=session_id in self._sessions
        _,d=self._session(session_id)
        loaded=time.perf_counter()
        if body.get('generation_id') != (d['asked'] or {}).get('generation_id'): raise ValueError('stale or unknown generation_id')
        items=body.get('items'); width=d['architecture'][0]
        if not isinstance(items,list) or not items: raise ValueError('items must be a non-empty list')
        indexes=[]; inputs=[]
        for item in items:
            cid=item.get('candidate_id','');
            if not cid.startswith('candidate-') or not cid[10:].isdigit() or int(cid[10:])>=len(d['candidates']): raise ValueError('unknown candidate_id')
            vector=item.get('input');
            if not isinstance(vector,list) or len(vector)!=width or any(type(v) not in (int,float) or v!=v or abs(v)==float('inf') for v in vector): raise ValueError(f'input must contain {width} values')
            indexes.append(int(cid[10:])); inputs.append(vector)
        before_prepare=time.perf_counter()
        layers,hit=self._layers(('session',session_id,body['generation_id']),d['architecture'],d['candidates'])
        prepared=time.perf_counter()
        out,ms=self.backend.predict_indexed(layers,indexes,inputs,normalization=d.get('normalization'))
        return {'generation_id':body['generation_id'],'backend':self.backend.name,'weights_cache_hit':hit,'session_cache_hit':session_hit,'timing_ms':{'session_load':(loaded-started)*1000,'prepare':(prepared-before_prepare)*1000,'model_compute_wall':ms},'items':[{'candidate_id':item['candidate_id'],'sample_id':item.get('sample_id'),'output':out[i]} for i,item in enumerate(items)]}
    @serialized
    def tell(self, session_id, body):
        _,d=self._session(session_id); rid=body.get('request_id')
        if rid and rid in d['request_ids']: return d['request_ids'][rid]
        if body.get('generation_id') != (d['asked'] or {}).get('generation_id'): raise ValueError('stale or unknown generation_id')
        scores=body.get('fitness'); expected=len(d['candidates'])
        if not isinstance(scores,list) or len(scores)!=expected: raise ValueError(f'fitness must contain exactly {expected} scores')
        active = d.get('mutation_active_inputs')
        if active is not None:
            used = self.active_inputs(body.get('used_inputs'), d['architecture'][0])
            active = [a or u for a,u in zip(active, used)]
        e=EvolutionSession(d['champion'],population_size=d['population_size'],elite_count=d['elite_count'],mutation_sigma=d['mutation_sigma'],seed=d['seed'],generation=d['generation']); e.candidates=d['candidates']; score,w=e.tell(scores)
        model=self.model(row_network := self._session(session_id)[0]['network_id']); old=DenseTanhCheckpoint.load(model['checkpoint']); new=old.with_weights(w,generation=old.payload.get('generation',0)+1,score=score)
        if active is not None:
            new.payload['mutation_active_inputs'] = active
            d['mutation_active_inputs'] = active
        target=Path(model['checkpoint']).with_name(f'checkpoint-g{new.payload["generation"]}.json'); new.save(target); cid=_hash(target)
        with self.connect() as db: db.execute('UPDATE models SET checkpoint=?, checkpoint_id=? WHERE network_id=?',(str(target),cid,row_network))
        d.update(champion=w,generation=e.generation,candidates=None,asked=None,checkpoint=str(target),checkpoint_id=cid); result={'checkpoint_id':cid,'generation':e.generation,'selected_candidate':'candidate-'+str(max(range(expected),key=lambda i:scores[i])),'score':score}; d['request_ids'][rid]=result; self._save(session_id,d); return result
