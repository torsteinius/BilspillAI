"""Read-only attribution of recorded decisions to checkpoint weights.

Run from the repository root. Uses selected attempts so each generation's saved
checkpoint is exactly the network that produced the recorded outputs.
"""
import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.network import NeuralNetwork

ACTIONS = ('forward', 'backward', 'right', 'left')


def trace(network, inputs, *, zero_bias_layers=(), zero_memory_weights=False):
    values = list(inputs)
    offset = 0
    layers = []
    for li, width in enumerate(network.architecture[1:]):
        stride = len(values) + 1
        rows = [network.weights[offset+n*stride:offset+(n+1)*stride] for n in range(width)]
        products = [[w*v if not (zero_memory_weights and li == 0 and i >= 8) else 0.
                     for i, (w, v) in enumerate(zip(row[:-1], values))] for row in rows]
        biases = [0. if li in zero_bias_layers else row[-1] for row in rows]
        pre = [sum(p)+b for p, b in zip(products, biases)]
        normalized = pre
        if network.metadata.get('normalization') == 'layernorm_hidden_v1' and li < len(network.architecture)-2:
            mean = sum(pre)/width
            scale = math.sqrt(sum((v-mean)**2 for v in pre)/width+1e-5)
            normalized = [(v-mean)/scale for v in pre]
        layers.append(dict(inputs=values, products=products, biases=biases, pre=pre, rows=rows))
        values = [math.tanh(v) for v in normalized]
        offset += width*stride
    return values, layers


def observations(frame, maze, count):
    values = [v/maze['sensor_range'] for v in frame['sensors']]
    values += [v for row in frame['memory'] for v in row]
    return values + [0.]*(count-len(values))


def diagnose(record, number, network):
    decisions = []
    for before, after in zip(record['frames'], record['frames'][1:]):
        inputs = observations(before, record['maze'], network.architecture[0])
        outputs, layers = trace(network, inputs)
        error = max(abs(a-b) for a, b in zip(outputs, after['output_values']))
        assert error < 1e-4, (number, after['steps'], error)
        assert ACTIONS[max(range(4), key=outputs.__getitem__)] == after['action']
        decisions.append((inputs, outputs, layers, after, error))
    # Inspect the first backward decision, or the initial decision if none.
    inputs, outputs, layers, after, error = next((d for d in decisions if d[3]['action']=='backward'), decisions[0])
    def result(xs, **kwargs):
        out, _ = trace(network, xs, **kwargs)
        return dict(outputs=dict(zip(ACTIONS, out)), action=ACTIONS[max(range(4), key=out.__getitem__)])
    last = layers[-1]
    competitor = max((i for i in range(4) if i != 1), key=outputs.__getitem__)
    contributions = []
    start = len(network.weights)-4*(len(last['inputs'])+1)
    for i, activation in enumerate(last['inputs']):
        contributions.append(dict(hidden_neuron_1based=i+1, activation=activation,
            backward_weight_index_0based=start+len(last['inputs'])+1+i,
            backward_weight=last['rows'][1][i], competitor_weight=last['rows'][competitor][i],
            backward_minus_competitor=last['products'][1][i]-last['products'][competitor][i]))
    zero_indices = [i for i in range(8, len(inputs)) if inputs[i] == 0.]
    return dict(attempt=number, generation=record['generation'], candidate=record['candidate'],
        score=record['score'], action_counts={a:sum(d[3]['action']==a for d in decisions) for a in ACTIONS},
        max_recorded_output_error=max(d[4] for d in decisions),
        inspected_step=after['steps'], inputs=inputs, outputs=dict(zip(ACTIONS,outputs)),
        empty_memory_input_count=len(zero_indices),
        empty_memory_max_contribution=max(abs(row[i]) for row in layers[0]['products'] for i in zero_indices),
        output_weighted_sums=[sum(p) for p in last['products']], output_biases=last['biases'],
        output_preactivations=last['pre'],
        ablations=dict(all_inputs_zero=result([0.]*len(inputs)),
            all_biases_zero=result(inputs, zero_bias_layers=range(len(layers))),
            all_inputs_and_biases_zero=result([0.]*len(inputs), zero_bias_layers=range(len(layers))),
            output_bias_zero=result(inputs, zero_bias_layers=[len(layers)-1]),
            memory_weights_zero=result(inputs, zero_memory_weights=True),
            each_layer_bias_zero=[result(inputs, zero_bias_layers=[i]) for i in range(len(layers))]),
        comparison_action=ACTIONS[competitor],
        strongest_output_contributions=sorted(contributions,key=lambda c:abs(c['backward_minus_competitor']),reverse=True)[:10])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--attempts', type=Path, default=Path('.ai-service/explore-fresh-50-attempts.jsonl'))
    p.add_argument('--checkpoints', type=Path, default=Path('.ai-service/normalized-experiment/generic-models/history-5-explore-fresh-2945118173'))
    p.add_argument('--numbers', type=int, nargs='+', default=[21, 225, 377, 399, 400])
    p.add_argument('--output', type=Path, default=Path('.ai-service/backward-weight-diagnosis.json'))
    args = p.parse_args()
    records = [json.loads(line) for line in args.attempts.read_text().splitlines() if line.strip()]
    report = []
    for number in args.numbers:
        record = records[number-1]
        assert record['selected'], 'Only selected candidates match saved generation checkpoints'
        network = NeuralNetwork.load(args.checkpoints/f"checkpoint-g{record['generation']}.json")
        item = diagnose(record, number, network)
        report.append(item)
        print(json.dumps({k:item[k] for k in ('attempt','generation','score','action_counts','max_recorded_output_error',
            'inspected_step','outputs','empty_memory_input_count','empty_memory_max_contribution',
            'output_weighted_sums','output_biases','ablations')}, indent=2))
    args.output.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
