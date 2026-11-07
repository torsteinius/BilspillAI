import unittest
from games.car.hybrid import select_winner

class AdaptationSelectionTests(unittest.TestCase):
    def test_five_generations_then_parent_returns(self):
        scores=[dict(score=100),dict(score=20),dict(score=30)]
        for generation in range(873,878):
            self.assertEqual(select_winner(scores,generation,872,adaptation_generations=5),2)
        self.assertEqual(select_winner(scores,878,872,adaptation_generations=5),0)
        self.assertEqual(scores[0]['score'],100)
    def test_existing_modes(self):
        scores=[dict(score=100),dict(score=20)]
        self.assertEqual(select_winner(scores,1,0),0)
        self.assertEqual(select_winner(scores,999,0,trained_only=True),1)
