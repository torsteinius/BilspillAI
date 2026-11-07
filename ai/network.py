"""Game-independent dense tanh network and evolutionary training (stdlib only)."""
import json
import math
import random
import tempfile
from pathlib import Path


class NeuralNetwork:
    """Layer sizes include input and output; each neuron stores weights then bias.

    Games normalize observations and supply evaluate(weights) -> finite score.
    Higher scores are better. No game rules or rendering belong in this class.
    """

    def __init__(self, architecture, *, seed=None):
        if len(architecture) < 2 or any(type(n) is not int or n < 1 for n in architecture):
            raise ValueError('Architecture needs at least two positive integer layer sizes')
        self.architecture = tuple(architecture)
        self.weight_count = sum((a + 1) * b for a, b in zip(architecture, architecture[1:]))
        self.weights = [0.] * self.weight_count
        self.seed = seed if seed is not None else random.SystemRandom().randrange(2**53)
        self.generation = 0
        self.score = None
        self.history = []
        self.metadata = {}
        self.backend = 'python'
        self._native = None

    def set_backend(self, backend):
        """Select a local engine explicitly; checkpoints remain engine-independent."""
        if backend not in ('python', 'rust'):
            raise ValueError('Local network backend must be python or rust')
        native = None
        if backend == 'rust':
            from ai.rust_backend import native_module
            native = native_module().DenseNetwork(list(self.architecture))
        self.backend, self._native = backend, native
        return self

    def _check_weights(self, weights):
        if len(weights) != self.weight_count or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in weights):
            raise ValueError('Weights must be finite and match the architecture')

    def forward(self, inputs, weights=None):
        weights = self.weights if weights is None else weights
        if len(inputs) != self.architecture[0] or len(weights) != self.weight_count:
            raise ValueError('Inputs and weights must match the architecture')
        if self.backend == 'rust':
            return self._native.forward(inputs, weights, self.metadata.get('normalization') == 'layernorm_hidden_v1')
        values, offset = list(inputs), 0
        for layer_index, width in enumerate(self.architecture[1:]):
            stride = len(values) + 1
            active = [(i, v) for i, v in enumerate(values) if v != 0.]
            values = [sum(weights[offset + n * stride + i] * v for i, v in active)
                      + weights[offset + n * stride + stride - 1] for n in range(width)]
            if self.metadata.get('normalization') == 'layernorm_hidden_v1' and layer_index < len(self.architecture)-2:
                mean = sum(values)/width
                variance = sum((v-mean)**2 for v in values)/width
                values = [(v-mean)/math.sqrt(variance+1e-5) for v in values]
            values = [math.tanh(v) for v in values]
            offset += width * stride
        return values

    def forward_batch(self, observations, weights=None):
        """Evaluate observations together, transferring weights once to Rust."""
        weights = self.weights if weights is None else weights
        if self.backend == 'rust':
            return self._native.forward_batch(observations, weights, self.metadata.get('normalization') == 'layernorm_hidden_v1')
        return [self.forward(inputs, weights) for inputs in observations]

    def expand_inputs(self, count):
        """Append zero-weight inputs, preserving predictions from the old inputs."""
        if type(count) is not int or count < 1:
            raise ValueError('Input expansion must be a positive integer')
        old_inputs, width = self.architecture[:2]
        expanded = type(self)((old_inputs + count,) + self.architecture[1:], seed=self.seed)
        rows = []
        for neuron in range(width):
            row = self.weights[neuron * (old_inputs + 1):(neuron + 1) * (old_inputs + 1)]
            rows.extend(row[:-1] + [0.] * count + row[-1:])
        expanded.weights = rows + self.weights[width * (old_inputs + 1):]
        expanded.set_backend(self.backend)
        return expanded

    def save(self, path):
        """Atomically replace a checkpoint, retaining experiment metadata/history."""
        self._check_weights(self.weights)
        payload = dict(self.metadata, format_version=1, architecture=list(self.architecture),
                       weights=self.weights, generation=self.generation, score=self.score,
                       seed=self.seed, history=self.history)
        data = json.dumps(payload, indent=2, allow_nan=False)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, encoding='utf-8') as stream:
                temporary = Path(stream.name)
                stream.write(data)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path, *, expected_architecture=None):
        saved = json.loads(Path(path).read_text(encoding='utf-8'))
        model_class = cls
        if saved.get('model_type') == 'present_history_branches_v1':
            from ai.branched import BranchedNetwork
            model_class = BranchedNetwork
        if saved.get('model_type') == 'sector_local_vision_v1':
            from ai.local_vision import LocalVisionNetwork
            model_class = LocalVisionNetwork
        if saved.get('model_type') == 'two_height_laser_local_v1':
            from ai.laser_vision import LaserVisionNetwork
            model_class = LaserVisionNetwork
        network = model_class(saved['architecture'], seed=saved.get('seed'))
        if expected_architecture is not None and network.architecture != tuple(expected_architecture):
            raise ValueError('Saved model has incompatible architecture')
        network._check_weights(saved['weights'])
        network.weights = saved['weights'][:]
        network.generation = saved.get('generation', 0)
        network.score = saved.get('score')
        if type(network.generation) is not int or network.generation < 0:
            raise ValueError('Invalid generation')
        if network.score is not None and not math.isfinite(network.score):
            raise ValueError('Invalid score')
        network.history = saved.get('history', [])
        reserved = {'format_version', 'architecture', 'weights', 'generation', 'score', 'seed', 'history'}
        network.metadata = {k: v for k, v in saved.items() if k not in reserved}
        return network

    def train(self, evaluate, generations, *, population_size=36, elite_count=6,
              initial_sigma=.35, mutation_sigma=.05, resume=False, checkpoint=None,
              on_candidate=None, on_result=None, on_generation=None, on_generation_start=None,
              evaluate_batch=None):
        """Train using selection/mutation; callbacks let games report progress.

        Resume re-evaluates the incumbent against the current objective. A new
        population is made on resume; this is not an exact optimizer-state replay.
        mutation_sigma may be a float or a function of the absolute generation.
        on_generation_start can change the evaluation set; the incumbent is
        re-scored after this callback, so scores from different sets never compete.
        """
        if type(generations) is not int or generations < 1:
            raise ValueError('Generations must be a positive integer')
        if not 1 <= elite_count <= population_size or initial_sigma < 0:
            raise ValueError('Invalid population, elite count or initial spread')
        start = self.generation if resume else 0
        sigmas = [mutation_sigma(g) if callable(mutation_sigma) else mutation_sigma
                  for g in range(start + 1, start + generations + 1)]
        if any(not math.isfinite(s) or s < 0 for s in sigmas):
            raise ValueError('Mutation spread must be finite and nonnegative')
        rng = random.Random(self.seed + start)
        native_rng = None
        if self.backend == 'rust':
            from ai.rust_backend import native_module
            native_rng = native_module().EvolutionRng(rng.getrandbits(64))

        def measured(weights):
            score = float(evaluate(weights))
            if not math.isfinite(score):
                raise ValueError('Evaluation must return a finite score')
            return score

        if resume:
            self.score = measured(self.weights) if on_generation_start is None else None
            mutations = (native_rng.mutate(self.weights, population_size - 1, .05) if native_rng else
                         [[v + rng.gauss(0, .05) for v in self.weights] for _ in range(population_size - 1)])
            population = [self.weights[:]] + mutations
        else:
            self.generation, self.score, self.history = 0, None, []
            population = (native_rng.mutate([0.] * self.weight_count, population_size, initial_sigma) if native_rng else
                          [[rng.gauss(0, initial_sigma) for _ in range(self.weight_count)] for _ in range(population_size)])
        for generation, sigma in zip(range(start + 1, start + generations + 1), sigmas):
            if on_generation_start:
                on_generation_start(generation)
                if (resume or generation > start + 1) and evaluate_batch is None:
                    self.score = measured(self.weights)
            batch_scores = None
            if evaluate_batch is not None:
                # Re-evaluate the incumbent and population on exactly the same tasks.
                if on_candidate:
                    on_candidate(generation, 0)
                batch_scores = list(evaluate_batch([self.weights[:]] + population))
                if len(batch_scores) != len(population) + 1 or any(not math.isfinite(v) for v in batch_scores):
                    raise ValueError('Batch evaluation must return one finite score per candidate')
                if resume or generation > start + 1:
                    self.score = batch_scores[0]
                batch_scores = batch_scores[1:]
            ranked = []
            for index, weights in enumerate(population, 1):
                if on_candidate:
                    on_candidate(generation, index)
                score = measured(weights) if batch_scores is None else batch_scores[index - 1]
                ranked.append((score, weights))
                if self.score is None or score > self.score:
                    self.score, self.weights = score, weights[:]
                if on_result:
                    on_result(self)
            ranked.sort(key=lambda item: item[0], reverse=True)
            elites = [w[:] for _, w in ranked[:elite_count]]
            if native_rng:
                population = native_rng.breed(elites, population_size, sigma)
            else:
                population = elites[:]
                while len(population) < population_size:
                    population.append([v + rng.gauss(0, sigma) for v in rng.choice(elites)])
            self.generation = generation
            self.history.append(dict(generation=generation, best_score=self.score,
                                     population_size=population_size, elite_count=elite_count,
                                     initial_sigma=initial_sigma, mutation_sigma=sigma,
                                     seed=self.seed, run_start=start, resumed=resume))
            if native_rng:
                self.history[-1].update(backend='rust', rng='chacha8-rand0.8-rand_distr0.4')
            if checkpoint:
                self.save(checkpoint)
            if on_generation:
                on_generation(self)
        return self.score
