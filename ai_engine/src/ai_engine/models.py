import json
import math
from pathlib import Path

class DenseTanhCheckpoint:
    """The portable JSON layout also used by the legacy NeuralNetwork class."""
    def __init__(self, payload):
        self.payload = dict(payload)
        self.architecture = tuple(payload['architecture'])
        self.weights = list(payload['weights'])
        if len(self.architecture) < 2 or any(type(v) is not int or v < 1 for v in self.architecture):
            raise ValueError('architecture must contain at least two positive integers')
        count = sum((a + 1) * b for a, b in zip(self.architecture, self.architecture[1:]))
        if len(self.weights) != count or any(type(v) not in (int, float) or not math.isfinite(v) for v in self.weights):
            raise ValueError('weights must be finite and match architecture')
    @classmethod
    def load(cls, path): return cls(json.loads(Path(path).read_text(encoding='utf-8')))
    def save(self, path): Path(path).write_text(json.dumps(self.payload, indent=2, allow_nan=False), encoding='utf-8')
    def with_weights(self, weights, *, generation=None, score=None):
        data = dict(self.payload); data['weights'] = list(weights)
        if generation is not None: data['generation'] = generation
        if score is not None: data['score'] = score
        return type(self)(data)
