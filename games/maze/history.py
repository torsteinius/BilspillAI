"""Deterministic landmark history, current observation first, no learned memory."""
import math
from functools import lru_cache
from pathlib import Path
from ai.network import NeuralNetwork
from .memory import MemoryEpisode,MOVES

VERSION='rays8_complete_landmark_history_v1'


def capacity(width,height):
    # Upper bound on unique interior places, including detector false positives.
    return (width-2)*(height-2)


def architecture(width,height):
    inputs=8*(1+capacity(width,height))
    return [inputs]+[math.ceil(inputs+(4-inputs)*i/4) for i in (1,2,3)]+[4]


@lru_cache(maxsize=1)
def detector():
    return NeuralNetwork.load(Path(__file__).with_name('history_detector.json'))


def widen_network(old,sizes):
    """Pad every layer with zero connections; preserve the original function."""
    if len(sizes)!=len(old.architecture) or any(b<a for a,b in zip(old.architecture,sizes)):
        raise ValueError('Only widening with unchanged layer count is supported')
    new=NeuralNetwork(sizes,seed=old.seed)
    src=dst=0
    for a,b,na,nb in zip(old.architecture,old.architecture[1:],sizes,sizes[1:]):
        for neuron in range(b):
            new.weights[dst+neuron*(na+1):dst+neuron*(na+1)+a]=old.weights[src+neuron*(a+1):src+neuron*(a+1)+a]
            new.weights[dst+neuron*(na+1)+na]=old.weights[src+neuron*(a+1)+a]
        src+=(a+1)*b;dst+=(na+1)*nb
    new.generation=old.generation;new.history=list(old.history);new.metadata=dict(old.metadata)
    return new


class HistoryEpisode(MemoryEpisode):
    def __post_init__(self):
        super().__post_init__()
        self.history_capacity=capacity(self.maze.width,self.maze.height)
        self.registered=set()
        self.output_values=[0.]*4
        self.landmark_signal=False

    def observations(self):
        current=[v/self.maze.sensor_range for v in self.sensors()]
        return current+[v for row in self.memory for v in row]+[0.]*(8*(self.history_capacity-len(self.memory)))

    def apply_outputs(self,values):
        if len(values)!=4 or any(not math.isfinite(v) for v in values) or self.done:
            raise ValueError('Expected four finite movement outputs in an active episode')
        self.output_values=list(values)
        self.landmark_signal=detector().forward([min(v,10.)/10. for v in self.sensors()])[0]>0
        position=self.x,self.y
        self.memory_written=self.landmark_signal and position not in self.registered
        if self.memory_written:
            # Store after choosing an action, so current observation is not duplicated
            # as a new historical entry in that decision's input.
            if len(self.memory)>=self.history_capacity:
                raise RuntimeError('History capacity invariant violated')
            self.memory.append(tuple(v/self.maze.sensor_range for v in self.sensors()))
            self.registered.add(position)
        return self.step(MOVES[max(range(4),key=lambda i:values[i])])

    def snapshot(self):
        state=super().snapshot()
        state.update(history_capacity=self.history_capacity,landmark_signal=self.landmark_signal,
                     memory=[list(row) for row in self.memory])
        return state
