"""Compare former Python kernels with Rust, keeping road geometry in Rust."""
import json
from pathlib import Path
import statistics
import time
from collections import deque
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car import app, rotating
from games.car.hybrid import clone_network, evaluate_suite
from games.car.temporal import forward_gradient


def python_gradient(network, inputs, index=0):
    backend=network.backend
    network.backend='python'
    try:return forward_gradient(network,inputs,index)
    finally:network.backend=backend


def old_means(network,inputs):
    return [python_gradient(network,inputs,i)[0] for i in range(network.architecture[-1])]


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    n=NeuralNetwork.load(args.model).set_backend('rust')
    app.configure_track('training',1000);app.configure_traffic('convoy')
    app.configure_radar(3.);app.RADAR_MODE='cone4relative';app.TRACK.set_backend('rust')
    timings={};weights={};evaluations={}
    for native in (False,True):
        label='rust' if native else 'previous_python_kernels'
        times=[];test_times=[]
        for repeat in range(3):
            actors=[clone_network(n) for _ in range(5)]
            with patch.object(app,'NATIVE_CAR_KERNELS',native), patch.object(rotating,'forward_gradient',forward_gradient if native else python_gradient), patch.object(rotating,'forward_latent',rotating.forward_latent if native else old_means):
                start=time.perf_counter()
                rotating.train_generation(actors,1000,5,app.initial(0),[deque() for _ in range(5)],771)
                times.append(time.perf_counter()-start)
                start=time.perf_counter();evaluations[label]=evaluate_suite(n,n,1000,[-8,0,8]);test_times.append(time.perf_counter()-start)
            weights[label]=[v for a in actors for v in a.weights]
        timings[label]=dict(training_seconds=times,evaluation_seconds=test_times)
    delta=max(abs(a-b) for a,b in zip(weights['rust'],weights['previous_python_kernels']))
    result=dict(model=str(args.model),generation=n.generation,training_attempts=25,evaluation_attempts=15,timings=timings,max_trained_weight_difference=delta,
        evaluation_score_difference=evaluations['rust']['score']-evaluations['previous_python_kernels']['score'],
        training_speedup=statistics.median(timings['previous_python_kernels']['training_seconds'])/statistics.median(timings['rust']['training_seconds']),
        evaluation_speedup=statistics.median(timings['previous_python_kernels']['evaluation_seconds'])/statistics.median(timings['rust']['evaluation_seconds']))
    args.output.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    assert delta < 1e-8, 'Training diverged beyond numerical tolerance'
    assert abs(result['evaluation_score_difference'])<1e-8

if __name__=='__main__':main()
