import random
import unittest
from scripts.train_route_matches import Point, BITS, match_reward, sample_batch, train_round, prepare_model
from games.maze.training import Trainer,Config
from pathlib import Path
import tempfile,json


class RouteMatchTests(unittest.TestCase):
    def test_only_whole_action_match_is_rewarded(self):
        for action,bits in BITS.items():
            for other,output in BITS.items():
                self.assertEqual(match_reward([1 if b else -1 for b in output],action),1 if action==other else -1)
        self.assertEqual(match_reward([0,0],'backward'),1)
        with self.assertRaises(ValueError):match_reward([float('nan'),1],'forward')

    def test_random_points_have_complete_memory_and_balance_sizes(self):
        routes={size:[[Point(tuple(range(4*(i+1))),'forward','r',1,i,size) for i in range(20)]]
                for size in ('5x5','8x8','18x18')}
        batch=sample_batch(routes,random.Random(41),60)
        self.assertEqual([sum(p.size==s for p in batch) for s in routes],[20,20,20])
        self.assertTrue(any(p.step>10 for p in batch[:10]))
        for p in batch:self.assertEqual(p.inputs(100)[:len(p.values)],list(range(4*(p.step+1))))

    def test_api_scores_only_route_match_and_keeps_history_at_arbitrary_points(self):
        points=[Point((.1,)*4,'forward','a',1,0,'5x5'),Point((.2,)*12,'right','b',2,15,'8x8')]
        class Client:
            def ask(self,*args):return dict(candidate_ids=['a','b'],generation_id='g')
            def candidate_predict(self,sid,gid,items):
                self.items=items
                return dict(backend='mlx-gpu',items=[dict(candidate_id=i['candidate_id'],sample_id=i['sample_id'],
                    output=([1,1] if i['sample_id']=='0' else [-1,1]) if i['candidate_id']=='a' else [-1,-1])
                    for i in reversed(items)])
            def tell(self,sid,gid,scores,*args,**kwargs):
                self.scores=scores;self.mask=kwargs['used_inputs']
                return dict(selected_candidate='a',score=scores[0],checkpoint_id='winner')
        client=Client();result=train_round(client,'session',points,40,1)
        self.assertEqual(client.scores,[1.,-1.])
        self.assertEqual(client.mask,[True]*12+[False]*28)
        self.assertEqual(client.items[1]['input'],[.2]*12+[0.]*28)
        self.assertEqual(result['samples'][1]['step'],15)

    def test_expansion_keeps_trained_function_and_never_resets_weights(self):
        with tempfile.TemporaryDirectory() as d:
            t=Trainer(Config(deterministic_history=True,start_in_field=False,
                history_sensor_count=4,history_output_encoding='bits2',history_memory_decay=.75,
                history_memory_floor=.25,history_newest_first=True),Path(d)/'model.json')
            rng=random.Random(21);t.network.weights=[rng.uniform(-.5,.5) for _ in t.network.weights]
            t.network.metadata['normalization']='layernorm_hidden_v1';t.network.generation=7000
            t.network.save(t.model)
            dataset=dict(student_input_count=1028,student_memory_decay=.75,student_memory_floor=.25,
                         student_newest_first=True,dimensions=[[5,5],[18,18]])
            source=json.loads(t.model.read_text());new=prepare_model(source,dataset)
            x=[.1]*40
            self.assertEqual(new.forward(x+[0.]*988),t.network.forward(x))
            self.assertEqual(new.generation,7000)
            self.assertEqual(source['curriculum']['width'],5)
            self.assertNotIn('training_objective',source)
            self.assertFalse(any(new.metadata['mutation_active_inputs'][40:]))
            self.assertFalse(new.metadata['training_objective']['other_rewards'])
            new.save(Path(d)/'expanded.json')
            self.assertEqual(Trainer.load(Path(d)/'expanded.json').network.architecture,new.architecture)
