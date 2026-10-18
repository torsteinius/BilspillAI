import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ai.network import NeuralNetwork
from games.maze.memory import VERSION
from games.maze.training import Config, Trainer
from games.maze.world import Maze, Rules
from scripts.collect_successful_routes import SensorOnlyWalker, collect_attempt, collect


class RouteCollectionTests(unittest.TestCase):
    def teacher(self):
        net=NeuralNetwork([88,6])
        net.metadata.update(observation_version=VERSION, config={'rules':{'memory_steps':40}})
        net.weights[88]=1.  # First of four movement outputs: forward.
        return SensorOnlyWalker(net)

    def trainer(self, path):
        return Trainer(Config(deterministic_history=True,start_in_field=False,
            history_sensor_count=4,history_output_encoding='bits2',
            history_memory_decay=.75,history_memory_floor=.25,history_newest_first=True,
            rules=Rules(until_failure=True,min_steps=0)),path)

    def test_teacher_gets_only_sensors_even_if_memory_weights_are_large(self):
        teacher=self.teacher()
        teacher.network.weights[8:88]=[999.]*80
        action, inputs, _=teacher.choose([.1]*8)
        self.assertEqual(action,'forward')
        self.assertEqual(inputs,[.1]*8+[0.]*80)
        with self.assertRaises(ValueError):teacher.choose([.1]*4)

    def test_success_records_real_history_before_each_action_and_replays_exactly(self):
        trainer=self.trainer(Path('unused.json'))
        maze=Maze('corner',('#####','#...E','#.###','#.###','#####'),(1,1),0)
        summary,route=collect_attempt(self.teacher(),trainer,maze,1)
        self.assertTrue(summary['escaped'])
        self.assertEqual(route['samples'][0]['history_count'],0)
        self.assertEqual(route['samples'][1]['history_count'],1)
        replay=trainer.make_episode(maze)
        for i,sample in enumerate(route['samples']):
            self.assertEqual(sample['observation'],replay.observations())
            self.assertEqual(sample['teacher_inputs'][8:],[0.]*80)
            replay.apply_outputs([1. if b else -1. for b in sample['target_bits']])
            self.assertEqual(replay.snapshot(),route['frames'][i+1])
        self.assertTrue(replay.escaped)

    def test_failure_and_truncation_never_enter_success_dataset(self):
        trainer=self.trainer(Path('unused.json'))
        rows=('#####','#...E','#####','#####','#####')
        result,route=collect_attempt(self.teacher(),trainer,Maze('wall',rows,(1,1),2),1)
        self.assertFalse(result['escaped']);self.assertIsNone(route)
        result,route=collect_attempt(self.teacher(),trainer,Maze('short',rows,(1,1),0),2,max_steps=1)
        self.assertTrue(result['truncated']);self.assertIsNone(route)

    def test_dataset_counts_failures_preserves_model_and_split_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'teacher.json'; student=root/'student.json'
            self.teacher().network.save(source); original=source.read_bytes()
            t=self.trainer(student);t.network.save(student)
            rows=('#####','#...E','#####','#####','#####')
            maze=Maze('known',rows,(1,1),0)
            with patch('scripts.collect_successful_routes.generate',return_value=maze):
                report=collect(source,student,root/'data',attempts=2)
            self.assertEqual(report['attempted'],2);self.assertEqual(report['successes'],2)
            self.assertEqual(report['distinct_layouts'],1)
            self.assertEqual(report['repeated_layout_attempts'],1)
            train=[json.loads(x) for x in (root/'data/train.jsonl').read_text().splitlines()]
            validation=[json.loads(x) for x in (root/'data/validation.jsonl').read_text().splitlines()]
            self.assertEqual(len(train)+len(validation),6)
            self.assertFalse({s['route_id'] for s in train}&{s['route_id'] for s in validation})
            self.assertEqual(source.read_bytes(),original)
            with self.assertRaises(FileExistsError):collect(source,student,root/'data',attempts=1)


    def test_mixed_sizes_are_balanced_and_padded_without_changing_native_observations(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'teacher.json';student=root/'student.json'
            self.teacher().network.save(source);self.trainer(student).network.save(student)
            def corridor(width,height,seed):
                rows=tuple(['#'*width,'#'+'.'*(width-2)+'E']+['#'*width]*(height-2))
                return Maze(str(seed),rows,(1,1),0)
            with patch('scripts.collect_successful_routes.generate',side_effect=corridor):
                report=collect(source,student,root/'mixed',attempts=6,sizes=[5,8,18])
            self.assertEqual(report['student_input_count'],1028)
            self.assertEqual(report['source_model_input_count'],40)
            self.assertEqual([v['attempted'] for v in report['by_size'].values()],[2,2,2])
            routes=[json.loads(x) for x in (root/'mixed/successful-routes.jsonl').read_text().splitlines()]
            native={(r['attempt'],s['step']):s['observation'] for r in routes for s in r['samples']}
            ids={}
            for split in ('train','validation'):
                data=[json.loads(x) for x in (root/'mixed'/f'{split}.jsonl').read_text().splitlines()]
                ids[split]={s['route_id'] for s in data}
                for sample in data:
                    raw=native[sample['attempt'],sample['step']]
                    self.assertEqual(sample['observation_native_count'],len(raw))
                    self.assertEqual(sample['observation'],raw+[0.]*(1028-len(raw)))
                    self.assertEqual(len(raw),4*(1+(sample['width']-2)*(sample['height']-2)))
            self.assertFalse(ids['train']&ids['validation'])
            self.assertEqual(Trainer.load(student).network.architecture[0],40)
