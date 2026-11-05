import unittest
from scripts.log_car_generation_progress import progress_rows

class GenerationProgressTests(unittest.TestCase):
    def test_winner_deltas_and_incomplete_generations(self):
        baseline=dict(score=-100.,distance=1000.,attempts=100,collisions=100)
        candidate=dict(score=-70.,distance=1500.,attempts=100,collisions=98)
        events=[dict(generation=0,evaluation=baseline),dict(generation=1,round=100),
                dict(generation=1,winner='learner-0',evaluations=[baseline,candidate]),
                dict(generation=2,winner='parent',evaluations=[candidate,baseline]),
                dict(generation=3,test_candidate=0,evaluation=candidate)]
        rows=progress_rows(events)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[1]['score_change'],30.)
        self.assertEqual(rows[1]['mean_distance'],15.)
        self.assertEqual(rows[1]['distance_change_from_start_pct'],50.)
        self.assertEqual(rows[1]['collision_reduction'],2)
        self.assertEqual(rows[2]['score_change'],0.)
        self.assertEqual(rows[2]['score_change_from_start'],30.)
        self.assertEqual(rows[2]['completed_without_collision'],2)
