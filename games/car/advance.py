"""Continue a car experiment without a web server or playback."""
import argparse
import json
from pathlib import Path
from ai.network import NeuralNetwork
from . import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('generations', type=int, nargs='?', default=100)
    parser.add_argument('--model', type=Path, default=app.MODEL)
    args = parser.parse_args()
    if args.generations < 1:
        parser.error('Generations must be positive')
    try:
        network = NeuralNetwork.load(args.model)
        if network.architecture[0] != app.INPUTS or network.architecture[-1] != 1:
            raise ValueError('Car models need nine inputs and one output')
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.error(str(error))
    app.network = network
    app.ARCHITECTURE = list(network.architecture)
    app.WEIGHT_COUNT = network.weight_count
    backup = args.model.with_name(args.model.stem + '_before_advance.json')
    network.save(backup)
    network.metadata.update(game='car', collision_penalty=app.COLLISION_PENALTY,
                            objective='obstacle_penalties_only', simulation_steps=650,
                            track='s_curve', observation_version='seven_rays_circular_radar_v1')
    network.metadata.pop('validation', None)
    start = network.generation

    def report(trained):
        if (trained.generation - start) % 10 == 0:
            print(f'Advanced {trained.generation-start}/{args.generations}: '
                  f'generation={trained.generation}, score={trained.score:.2f}', flush=True)

    network.train(lambda weights: app.evaluate(weights)[0], args.generations,
                  resume=True, checkpoint=args.model, on_generation=report)
    network.metadata['validation'] = [app.evaluate(network.weights, offset) for offset in (-8, 0, 8)]
    network.save(args.model)
    print(json.dumps(network.metadata['validation']), flush=True)


if __name__ == '__main__':
    main()
