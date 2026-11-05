"""Continue a car experiment without a web server or playback."""
import argparse
import json
from pathlib import Path
from ai.network import NeuralNetwork
from . import app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('generations', type=int, nargs='?', default=100)
    parser.add_argument('--fresh', action='store_true', help='Train from random weights in a new model file')
    parser.add_argument('--seed', type=int, default=20261105)
    parser.add_argument('--backend', choices=('python', 'rust'), default='python')
    parser.add_argument('--traffic', choices=('convoy', 'opposite'))
    parser.add_argument('--track', choices=app.Track.NAMES, help='Defaults to the model’s saved track')
    parser.add_argument('--steps', type=int, help='Simulation steps per attempt')
    parser.add_argument('--model', type=Path, default=app.MODEL)
    args = parser.parse_args()
    if args.steps is not None and args.steps < 1:
        parser.error('--steps must be positive')
    if args.generations < 1:
        parser.error('Generations must be positive')
    try:
        if args.fresh and args.model.exists():
            raise ValueError('--fresh requires a new model path; existing weights are preserved')
        network = (NeuralNetwork([23, 8, 8, 1], seed=args.seed) if args.fresh else NeuralNetwork.load(args.model)).set_backend(args.backend)
        if args.fresh:
            network.metadata.update(track='training', traffic='convoy', radar_mode='cone4', radar_scale=3.)
        elif network.metadata.get('observation_version') != 'seven_rays_four_cone_targets_v5':
            raise ValueError('Radar visibility changed; use --fresh with a new model path')
        if network.architecture[0] != 23 or network.architecture[-1] != 1:
            raise ValueError('Car models need twenty-three inputs and one output')
    except (ValueError, KeyError, OSError, TypeError, RuntimeError) as error:
        parser.error(str(error))
    saved_track = network.metadata.get('track', 's_curve')
    selected_track = args.track or saved_track
    steps = args.steps
    if steps is None and selected_track == saved_track:
        steps = network.metadata.get('simulation_steps')
    app.configure_track(selected_track, steps)
    app.TRACK.set_backend(args.backend)
    app.configure_traffic(args.traffic or network.metadata.get('traffic', 'opposite'))
    app.RADAR_MODE = network.metadata.get('radar_mode', 'legacy')
    app.configure_radar(network.metadata.get('radar_scale', 1.))
    app.network = network
    app.ARCHITECTURE = list(network.architecture)
    app.WEIGHT_COUNT = network.weight_count
    backup = args.model.with_name(args.model.stem + '_before_advance.json')
    if not args.fresh:
        network.save(backup)
    network.metadata.update(game='car', training_backend=args.backend, geometry_backend=args.backend, collision_penalty=app.COLLISION_PENALTY,
                            objective='obstacle_penalties_only', simulation_steps=app.SIMULATION_STEPS,
                            track=app.TRACK.name, traffic=app.TRAFFIC, radar_mode=app.RADAR_MODE, radar_scale=app.RADAR_SCALE,
                            speed_factors=list(app.SPEED_FACTORS) if app.TRAFFIC == 'convoy' else [1.,1.],
                            radar_occlusion='none', observation_version='seven_rays_four_cone_targets_v5')
    network.metadata.pop('validation', None)
    network.save(args.model)
    start = network.generation

    def report(trained):
        if (trained.generation - start) % 10 == 0:
            print(f'Advanced {trained.generation-start}/{args.generations}: '
                  f'generation={trained.generation}, score={trained.score:.2f}', flush=True)

    network.train(lambda weights: app.evaluate(weights)[0], args.generations,
                  resume=not args.fresh, mutation_sigma=lambda gen: .12 if gen < 40 else .05, checkpoint=args.model, on_generation=report)
    network.metadata['validation'] = [app.evaluate(network.weights, offset) for offset in (-8, 0, 8)]
    network.save(args.model)
    print(json.dumps(network.metadata['validation']), flush=True)


if __name__ == '__main__':
    main()
