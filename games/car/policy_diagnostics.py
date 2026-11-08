"""Deterministic road observations and input-sensitivity checks for policies."""
import math

from . import app


def fixed_observations(actor, seed, starts_per_direction=12):
    """120 poses in both driving directions, independent of training RNGs."""
    from .hybrid import features
    from .scenarios import Scenario
    cones = app.TRACK.cones
    try:
        observations = []
        for generation in (1, 2):
            scenario = Scenario(seed + 700001, generation, no_cones=True)
            for cars in scenario.evaluation_starts(starts_per_direction):
                observations.extend(features(car, cars, actor) for car in cars)
        return observations
    finally:
        app.TRACK.cones = cones


def policy_diagnostics(actor, observations):
    """Report output ranges and hidden activations on the same saved inputs.

    Saturation means abs(tanh activation) >= .99. Sign-change fraction counts
    neurons with both positive and negative activations across the probe set.
    """
    if not observations:
        raise ValueError('Diagnostics require observations')
    layers = [[] for _ in actor.architecture[1:-1]]
    outputs = []
    for inputs in observations:
        if hasattr(actor, '_activations'):
            activations, _ = actor._activations(inputs, actor.weights)
        else:
            activations = [inputs]
            offset = 0
            for index, width in enumerate(actor.architecture[1:]):
                previous = activations[-1]
                stride = len(previous) + 1
                values = [sum(actor.weights[offset+n*stride+i]*v
                              for i, v in enumerate(previous))
                          + actor.weights[offset+n*stride+stride-1]
                          for n in range(width)]
                activations.append(values if index == len(actor.architecture)-2
                                   else [math.tanh(v) for v in values])
                offset += width*stride
        for collected, values in zip(layers, activations[1:-1]):
            collected.append(values)
        outputs.append([math.tanh(v) for v in activations[-1]])
    hidden = []
    for index, rows in enumerate(layers):
        width = len(rows[0])
        hidden.append(dict(
            layer=index+1, width=width,
            saturated_fraction=sum(abs(v) >= .99 for row in rows for v in row)
                               / (len(rows)*width),
            sign_change_fraction=sum(min(column) < 0 < max(column)
                                     for column in zip(*rows))/width))
    ranges = [dict(min=min(column), max=max(column), span=max(column)-min(column))
              for column in zip(*outputs)]
    return dict(observations=len(observations), saturation_threshold=.99,
                steering=ranges[0], outputs=ranges, hidden_layers=hidden)
