"""Game-specific evaluations and automatic 50% curriculum growth."""
from dataclasses import asdict, dataclass, field, replace
import threading
import hashlib
import json
from ai.network import NeuralNetwork
from .generator import generate, generate_field, next_size
from .memory import MemoryEpisode, VERSION as MEMORY_VERSION
from .history import HistoryEpisode, VERSION as HISTORY_VERSION, architecture as history_architecture, widen_network
from .world import Episode, OBSERVATION_VERSION, Rules, decode_outputs


@dataclass
class Config:
    deterministic_history: bool = False
    learned_memory: bool = False
    start_in_field: bool = True
    field_size: int = 30
    field_stones: int = 50
    field_stones_step: int = 25
    field_stones_max: int = 100
    width: int = 5
    height: int = 5
    stages: int = 4
    seed: int = 42
    population: int = 36
    train_mazes: int = 8
    validation_mazes: int = 20
    check_every: int = 5
    success_streak: int = 20
    hidden: list = field(default_factory=lambda: [12, 8])
    rules: Rules = field(default_factory=Rules)

    def __post_init__(self):
        if self.deterministic_history and (self.learned_memory or self.start_in_field):
            raise ValueError("Deterministic history requires maze mode without learned memory")
        generate_field(self.field_size, self.field_stones, seed=self.seed)
        generate_field(self.field_size, self.field_stones_max, seed=self.seed)
        if self.field_stones_step < 1 or self.field_stones_max < self.field_stones:
            raise ValueError('Invalid stone progression')
        if min(self.width, self.height) < 5:
            raise ValueError('Start dimensions must be at least 5')
        for name in ('stages', 'population', 'train_mazes', 'validation_mazes', 'check_every', 'success_streak'):
            if getattr(self, name) < 1:
                raise ValueError(f'{name} must be positive')
        if self.train_mazes < 2:
            raise ValueError('Use at least two training mazes to avoid repeated layouts')


class Trainer:
    def __init__(self, config, model):
        self.backend = "python"
        self.config, self.model = config, model
        self.network = NeuralNetwork([8 + 2 * config.rules.memory_steps if config.learned_memory else config.rules.input_count,
                                      *config.hidden, 6 if config.learned_memory else 2], seed=config.seed)
        if config.deterministic_history:
            self.network = NeuralNetwork(history_architecture(config.width, config.height), seed=config.seed)
        self.field_stones = config.field_stones
        self.stage = -1 if config.start_in_field else 0
        self.width, self.height = (config.field_size, config.field_size) if config.start_in_field else (config.width, config.height)
        self.check_index, self.streak = 0, 0
        self.evaluations = []
        self.sequence = dict(training=0, validation=0, replay=0)
        self.recent = dict(training=[], validation=[], replay=[])
        self.streak_model = None
        self.lock = threading.Lock()
        self.recording = None
        self.training_attempts = 0
        self.recording_id = 0
        self.replay_index = 0
        self.replay_lock = threading.Lock()
        self.recent_recordings = []
        self.status = dict(phase='ready', generation=0, candidate=0, score=None,
                           success=None, error=None, architecture=list(self.network.architecture))
        self._metadata()

    @classmethod
    def load(cls, model):
        network = NeuralNetwork.load(model)
        meta = network.metadata
        if meta.get('game') != 'maze' or meta.get('observation_version') not in (OBSERVATION_VERSION, MEMORY_VERSION, HISTORY_VERSION):
            raise ValueError('This is not a compatible maze checkpoint')
        values = dict(meta['config'])
        values.setdefault('start_in_field', False)
        values.setdefault('field_stones_max', values.get('field_stones',50))
        values.pop('required_success', None)
        values.pop('growth_checks', None)
        values['rules'] = Rules(**values['rules'])
        trainer = cls(Config(**values), model)
        expected = HISTORY_VERSION if trainer.config.deterministic_history else MEMORY_VERSION if trainer.config.learned_memory else OBSERVATION_VERSION
        if meta['observation_version'] != expected:
            raise ValueError('Observation version does not match mode')
        if trainer.config.deterministic_history:
            state = meta['curriculum']
            trainer.network = NeuralNetwork(history_architecture(state['width'], state['height']), seed=network.seed)
        if network.architecture != trainer.network.architecture:
            raise ValueError('Saved architecture does not match the episode memory')
        trainer.network = network
        state = meta['curriculum']
        trainer.stage, trainer.width, trainer.height = state['stage'], state['width'], state['height']
        trainer.field_stones = state.get('field_stones', trainer.config.field_stones)
        trainer.check_index = state['check_index']
        if meta.get('progression_version') == 2:
            trainer.streak = state['streak']
            trainer.sequence = state['sequence']
            trainer.recent = {key: [tuple(rows) for rows in layouts] for key, layouts in state['recent'].items()}
            trainer.streak_model = state.get('streak_model')
        if meta.get('success_criterion') != 'exit_without_collision_or_stall_v1':
            trainer.streak = 0
            trainer.streak_model = None
        trainer.evaluations = list(meta.get('evaluations', []))
        trainer.status.update(generation=network.generation, score=network.score, architecture=list(network.architecture))
        if trainer.evaluations:
            last = trainer.evaluations[-1]
            if (last['width'], last['height']) == (trainer.width, trainer.height):
                trainer.status['success'] = last['success_rate']
        return trainer

    def _metadata(self):
        self.network.metadata.update(game='maze', success_criterion='exit_without_collision_or_stall_v1', progression_version=2, observation_version=HISTORY_VERSION if self.config.deterministic_history else MEMORY_VERSION if self.config.learned_memory else OBSERVATION_VERSION,
            config=asdict(self.config), curriculum=dict(stage=self.stage, width=self.width,
                height=self.height, field_stones=self.field_stones, check_index=self.check_index, streak=self.streak,
                sequence=self.sequence, recent=self.recent, streak_model=self.streak_model),
            evaluations=self.evaluations)

    def maze(self, index, validation=False):
        # Disjoint integer seed namespaces; fresh validation set at every check.
        seed = (self.config.seed << 40) + (self.stage << 32)
        seed += (1 << 31) + self.check_index * self.config.validation_mazes + index if validation else index
        return self.generate_environment(seed)

    def generate_environment(self, seed):
        if self.stage < 0:
            return generate_field(self.config.field_size, self.field_stones, seed=seed)
        return generate(self.width, self.height, seed=seed)

    def fresh_maze(self, stream):
        # Compare actual wall layouts, not seed/name/start position.
        offset = dict(training=0, validation=1 << 31, replay=1 << 30)[stream]
        for _ in range(1000):
            seed = (self.config.seed << 40) + (self.stage << 32) + offset + self.sequence[stream]
            self.sequence[stream] += 1
            maze = self.generate_environment(seed)
            if maze.rows in self.recent[stream]:
                continue
            if stream == 'replay' and self.recording and list(maze.rows) == list(self.recording['maze']['rows']):
                continue
            self.recent[stream] = (self.recent[stream] + [maze.rows])[-2:]
            return maze
        raise RuntimeError('Could not generate a different maze')

    def count_result(self, escaped):
        fingerprint = hashlib.sha256(json.dumps(self.network.weights).encode()).hexdigest()
        if fingerprint != self.streak_model:
            self.streak = 0
            self.streak_model = fingerprint
        self.streak = self.streak + 1 if escaped else 0

    def grow_if_ready(self):
        if self.streak < self.config.success_streak or self.stage + 1 >= self.config.stages:
            return False
        suffix = f'field_{self.field_stones}' if self.stage < 0 else f'{self.width}x{self.height}'
        completed = self.model.with_name(f'{self.model.stem}_{suffix}{self.model.suffix}')
        self._metadata()
        self.network.save(completed)
        if self.stage < 0 and self.field_stones < self.config.field_stones_max:
            self.field_stones = min(self.config.field_stones_max, self.field_stones+self.config.field_stones_step)
        else:
            self.width, self.height = (self.config.width, self.config.height) if self.stage < 0 else next_size(self.width, self.height)
            self.stage += 1
        if self.config.deterministic_history:
            self.network = widen_network(self.network, history_architecture(self.width, self.height))
            with self.lock:
                self.status["architecture"] = list(self.network.architecture)
        self.network.score = None
        self.streak = 0
        self.streak_model = None
        with self.lock:
            self.status.update(score=None, success=None)
        return True

    def rollout(self, maze, weights, record=False):
        episode = (HistoryEpisode if self.config.deterministic_history else MemoryEpisode if self.config.learned_memory else Episode)(maze, self.config.rules)
        frames = []
        def frame():
            state = episode.snapshot()
            state.pop('history')  # The ordered frames themselves contain the entire path.
            frames.append(state)
        if record:
            frame()
        while not episode.done:
            output = self.network.forward(episode.observations(), weights)
            episode.output_values = list(output)
            if self.config.learned_memory or self.config.deterministic_history:
                episode.apply_outputs(output)
            else:
                episode.step(decode_outputs(output))
            if record:
                frame()
        if record:
            with self.lock:
                if len(self.recent_recordings) == 2 and all(rows == maze.rows for rows in self.recent_recordings):
                    return episode
                self.recent_recordings = (self.recent_recordings + [maze.rows])[-2:]
                self.recording_id += 1
                self.recording = dict(id=self.recording_id, maze=maze.payload(), frames=frames,
                                      generation=self.status['generation'], candidate=self.status['candidate'])
        return episode

    def evaluate(self, weights):
        scores = []
        for maze in self.training_set:
            self.training_attempts += 1
            # Ten full-speed attempts without snapshots, then record one.
            episode = self.rollout(maze, weights, record=self.training_attempts % 11 == 0)
            scores.append(episode.score)
        return sum(scores) / len(scores)

    def evaluate_batch(self, populations):
        from ai.mlx_backend import BatchedNetwork
        if not (self.config.learned_memory or self.config.deterministic_history):
            raise ValueError('GPU batch evaluation currently requires learned-memory mode')
        batch = BatchedNetwork(self.network.architecture, populations)
        episode_type = HistoryEpisode if self.config.deterministic_history else MemoryEpisode
        episodes = [[episode_type(maze, self.config.rules) for maze in self.training_set]
                    for _ in populations]
        while True:
            outputs = batch.forward([[e.observations() for e in group] for group in episodes])
            active = False
            for group, group_outputs in zip(episodes, outputs):
                for episode, output in zip(group, group_outputs):
                    if not episode.done:
                        episode.apply_outputs(output)
                    active |= not episode.done
            if not active:
                break
        self.training_attempts += len(populations) * len(self.training_set)
        return [sum(e.score for e in group) / len(group) for group in episodes]

    def validate(self):
        results, seeds = [], []
        for i in range(self.config.validation_mazes):
            maze = self.fresh_maze('validation')
            episode = self.rollout(maze, self.network.weights, record=i == 0)
            results.append(episode)
            seeds.append(maze.name)
            self.count_result(episode.clean_success)
            if self.streak >= self.config.success_streak:
                break
        success = sum(episode.clean_success for episode in results) / len(results)
        self.evaluations.append(dict(generation=self.network.generation, stage=self.stage,
            width=self.width, height=self.height, environment='field' if self.stage < 0 else 'maze', check=self.check_index, success_rate=success,
            field_stones=self.field_stones if self.stage < 0 else None, sample_count=len(results), mean_score=sum(e.score for e in results)/len(results),
            streak=self.streak, mazes=seeds))
        self.check_index += 1
        with self.lock:
            self.status.update(success=success)
        return success

    def run(self, generations):
        if generations < 1:
            raise ValueError('Generations must be positive')
        target = self.network.generation + generations
        with self.lock:
            self.status.update(phase='training', target=target)
        try:
            while self.network.generation < target:
                def new_generation(generation):
                    self.training_set = [self.fresh_maze('training') for _ in range(self.config.train_mazes)]
                self._metadata()

                def candidate(generation, index):
                    with self.lock:
                        self.status.update(generation=generation, candidate=index, phase='training')

                def result(network):
                    with self.lock:
                        self.status['score'] = network.score

                def completed_generation(network):
                    network.history[-1].update(environment='field' if self.stage < 0 else 'maze', stage=self.stage, width=self.width, height=self.height,
                                               field_stones=self.field_stones if self.stage < 0 else None, train_mazes=self.config.train_mazes,
                                               mazes=[maze.name for maze in self.training_set])
                    if self.backend == 'mlx-gpu':
                        # Record the selected model once per generation, on CPU.
                        self.rollout(self.training_set[0], network.weights, record=True)
                    self._metadata()
                    network.save(self.model)

                self.network.train(self.evaluate, min(self.config.check_every, target-self.network.generation),
                    population_size=self.config.population, elite_count=min(6, self.config.population),
                    mutation_sigma=.12, resume=self.network.generation > 0,
                    on_candidate=candidate, on_result=result, on_generation=completed_generation,
                    on_generation_start=new_generation,
                    evaluate_batch=self.evaluate_batch if self.backend == "mlx-gpu" else None)
                with self.lock:
                    self.status['phase'] = 'validation'
                self.validate()
                self.grow_if_ready()
                self._metadata()
                self.network.save(self.model)
            self.apply_planned_growth()
            self.replay()
        except Exception as error:
            with self.lock:
                self.status.update(phase='error', error=str(error))
            raise

    def apply_planned_growth(self):
        """Apply a user-requested transition after a fixed training budget."""
        plan = self.network.metadata.get('planned_growth')
        if not plan or self.network.generation < plan['after_generation']:
            return False
        if self.stage < 0:
            raise ValueError('Planned maze growth requires a maze stage')
        backup = self.model.with_name(f'{self.model.stem}_before_growth{self.model.suffix}')
        self._metadata()
        self.network.save(backup)
        self.width, self.height = next_size(self.width, self.height)
        self.stage += 1
        self.config = replace(self.config, stages=self.stage+1)
        self.streak = 0
        self.streak_model = None
        self.network.score = None
        self.network.metadata['completed_planned_growth'] = self.network.metadata.pop('planned_growth')
        with self.lock:
            self.status.update(score=None, success=None)
        self._metadata()
        self.network.save(self.model)
        return True

    def replay(self):
        with self.lock:
            self.status.update(phase='replay', candidate=0, generation=self.network.generation)
        self.next_replay()

    def next_replay(self):
        """Fresh demonstration, separate from training and validation evidence."""
        with self.replay_lock:
            with self.lock:
                if self.status['phase'] != 'replay':
                    raise ValueError('New demonstrations are only available after training')
            self.grow_if_ready()
            maze = self.fresh_maze('replay')
            episode = self.rollout(maze, self.network.weights, record=True)
            self.count_result(episode.clean_success)
            self._metadata()
            self.network.save(self.model)
            with self.lock:
                return self.recording

    def payload(self):
        with self.lock:
            return dict(self.status, backend=self.backend, deterministic_history=self.config.deterministic_history, learned_memory=self.config.learned_memory, environment='field' if self.stage < 0 else 'maze', first_maze=[self.config.width,self.config.height], width=self.width, height=self.height, stage=self.stage+1,
                        stages=self.config.stages, streak=self.streak, success_streak=self.config.success_streak,
                        planned_growth=self.network.metadata.get('planned_growth'),
                        population=self.config.population, field_stones=self.field_stones,
                        next_field_stones=min(self.config.field_stones_max,self.field_stones+self.config.field_stones_step) if self.field_stones < self.config.field_stones_max else None,
                        rules=asdict(self.config.rules), recording=self.recording,
                        training_attempts=self.training_attempts, background_attempts=10,
                        evaluations=list(self.evaluations[-20:]))
