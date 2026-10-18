"""Create a fresh, evenly tapered history model from an existing model's rules.

Run from the repository root with python -m scripts.create_deep_history_model.
"""
import argparse
import copy
import math
import random
from dataclasses import asdict, replace
from pathlib import Path
from ai.network import NeuralNetwork
from games.maze.history import architecture
from games.maze.training import Trainer, history_version
from games.maze.world import Rules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('games/maze/models/deterministic_history_v1.json'))
    parser.add_argument('--output', type=Path, default=Path('.ai-service/deep-history-23.json'))
    parser.add_argument('--hidden-layers', type=int, default=23)
    parser.add_argument('--freeze-unused-memory', action='store_true')
    parser.add_argument('--normalize-hidden', action='store_true')
    parser.add_argument('--output-encoding', choices=('argmax4', 'bits2'), default='argmax4')
    parser.add_argument('--sensor-count', type=int, choices=(4, 8))
    parser.add_argument('--memory-decay', type=float)
    parser.add_argument('--memory-floor', type=float)
    parser.add_argument('--newest-first', action='store_true', default=None)
    parser.add_argument('--seed',type=int,default=42,help='Random seed for fresh weights')
    parser.add_argument('--min-steps', type=int, help='Override the source rules (0 = wall or loop ends at once)')
    parser.add_argument('--wall-penalty', type=float, help='Override the source rules')
    parser.add_argument('--revisit-penalty', type=float, help='Override the source rules')
    parser.add_argument('--reward-version', help='Label stored in the model metadata when rules change')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new path')
    original = Trainer.load(args.source)
    if not original.config.deterministic_history:
        parser.error('Source must use deterministic history')
    settings = {f'history_{key}': getattr(args, key) for key in ('sensor_count', 'memory_decay', 'memory_floor', 'newest_first') if getattr(args, key) is not None}
    config = replace(original.config, history_hidden_layers=args.hidden_layers,
                     history_output_encoding=args.output_encoding, **settings)
    model = NeuralNetwork(architecture(original.width, original.height, args.hidden_layers, args.output_encoding, config.history_sensor_count), seed=args.seed)
    rng = random.Random(model.seed)
    model.weights = []
    for inputs, outputs in zip(model.architecture, model.architecture[1:]):
        limit = math.sqrt(6 / (inputs + outputs))
        for _ in range(outputs):
            model.weights.extend(rng.uniform(-limit, limit) for _ in range(inputs))
            model.weights.append(0.)
    model.metadata = copy.deepcopy(original.network.metadata)
    model.metadata['config'] = asdict(config)
    model.metadata['observation_version'] = history_version(config)
    model.metadata['evaluations'] = []
    overrides = {name: getattr(args, name) for name in ('min_steps', 'wall_penalty', 'revisit_penalty')
                 if getattr(args, name) is not None}
    if overrides:
        rules = dict(model.metadata['config']['rules'], **overrides)
        Rules(**rules)  # validate before saving
        model.metadata['config']['rules'] = rules
    if args.reward_version:
        model.metadata['reward_version'] = args.reward_version
    state = model.metadata['curriculum']
    state.update(check_index=0, streak=0, streak_model=None,
                 sequence=dict(training=0, validation=0, replay=0),
                 recent=dict(training=[], validation=[], replay=[]))
    if args.freeze_unused_memory:
        model.metadata['mutation_active_inputs'] = [i < config.history_sensor_count for i in range(model.architecture[0])]
        stride = model.architecture[0] + 1
        for neuron in range(model.architecture[1]):
            for i in range(config.history_sensor_count, model.architecture[0]):
                model.weights[neuron * stride + i] = 0.
    if args.normalize_hidden:
        model.metadata['normalization'] = 'layernorm_hidden_v1'
    model.save(args.output)
    Trainer.load(args.output)
    print('Architecture:', model.architecture)
    print('Parameters:', model.weight_count)
    print('Saved:', args.output)


if __name__ == '__main__':
    main()
