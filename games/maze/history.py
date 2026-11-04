"""Deterministic landmark history, current observation first, no learned memory."""
import math
from functools import lru_cache
from pathlib import Path
from ai.network import NeuralNetwork
from .memory import MemoryEpisode,MOVES
from .world import DIRECTIONS

VERSION='rays8_complete_landmark_history_v1'
VERSION_V2='configurable_landmark_history_v2'
VERSION_V3='landmark_choice_history_v3'
VERSION_V4='action_only_history_v4'
CHOICE_BITS = {'backward': (-1., -1.), 'right': (-1., 1.),
               'left': (1., -1.), 'forward': (1., 1.)}
OUTPUT_ENCODINGS = ('argmax4', 'bits2')


def decode_bits(values):
    if len(values) != 2 or any(not math.isfinite(v) for v in values):
        raise ValueError('Expected two finite movement outputs')
    return ('backward', 'right', 'left', 'forward')[2 * int(values[0] > 0) + int(values[1] > 0)]


def capacity(width,height):
    # Upper bound on unique interior places, including detector false positives.
    return (width-2)*(height-2)


def architecture(width,height,hidden_layers=3,output_encoding='argmax4',sensor_count=8, choice_memory=False, action_memory_steps=0):
    if type(hidden_layers) is not int or hidden_layers < 1:
        raise ValueError("hidden_layers must be a positive integer")
    if output_encoding not in OUTPUT_ENCODINGS:
        raise ValueError('Unknown history output encoding')
    if sensor_count not in (4, 8):
        raise ValueError('History requires four or eight sensors')
    inputs=sensor_count+2*action_memory_steps if action_memory_steps else sensor_count+(sensor_count+2*choice_memory)*capacity(width,height)
    outputs = 2 if output_encoding == 'bits2' else 4
    return [inputs]+[math.ceil(inputs+(outputs-inputs)*i/(hidden_layers+1)) for i in range(1,hidden_layers+1)]+[outputs]


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
    new.set_backend(old.backend)
    return new


class HistoryEpisode(MemoryEpisode):
    def __init__(self, maze, rules, *, output_encoding='argmax4', sensor_count=8,
                 memory_decay=1., memory_floor=1., newest_first=False, choice_memory=False, action_memory_steps=0):
        if output_encoding not in OUTPUT_ENCODINGS:
            raise ValueError('Unknown history output encoding')
        self.output_encoding = output_encoding
        if sensor_count not in (4, 8):
            raise ValueError('History requires four or eight sensors')
        if not 0 < memory_decay <= 1 or not 0 <= memory_floor <= 1:
            raise ValueError('Invalid memory attenuation')
        if type(action_memory_steps) is not int or action_memory_steps < 0 or (action_memory_steps and choice_memory):
            raise ValueError("Invalid action-only memory settings")
        self.action_memory_steps = action_memory_steps
        self.choice_memory = choice_memory
        self.memory_row_width = 2 if action_memory_steps else sensor_count + 2 * choice_memory
        self.memory_places = []
        self.sensor_count = sensor_count
        self.sensor_angles = tuple(range(0, 360, 360 // sensor_count))
        self.memory_decay, self.memory_floor = memory_decay, memory_floor
        self.newest_first = newest_first
        super().__init__(maze, rules)

    def __post_init__(self):
        super().__post_init__()
        self.history_capacity=self.action_memory_steps or capacity(self.maze.width,self.maze.height)
        self.registered=set()
        self.rewarded_landmarks={(self.x, self.y)}
        self.output_values=[0.]*(2 if self.output_encoding == 'bits2' else 4)
        self.landmark_signal=False

    def landmark_kind(self):
        if self.maze.cell(self.x, self.y) != ".":
            return None
        openings = [i for i, (dx, dy) in enumerate(DIRECTIONS)
                    if self.maze.cell(self.x + dx, self.y + dy) in ".E"]
        if len(openings) >= 3:
            return "junction"
        if len(openings) == 2 and (openings[1] - openings[0]) % 2 == 1:
            return "corner"
        return None

    def first_visit_reward(self, point):
        return self.rules.exploration_reward

    def step(self, action):
        old = self.x, self.y
        reward = super().step(action)
        position = self.x, self.y
        if position != old and self.visits[position] == 1 and self.landmark_kind() and position not in self.rewarded_landmarks:
            self.rewarded_landmarks.add(position)
            reward += self.rules.landmark_reward
            self.score += self.rules.landmark_reward
            self.last_reward = reward
        return reward

    def sensors(self):
        return [self.maze.ray(self.x, self.y, self.heading, angle) for angle in self.sensor_angles]

    def input_memory(self):
        rows = list(reversed(self.memory)) if self.newest_first else list(self.memory)
        scales = [max(self.memory_floor, self.memory_decay ** (i + 1)) for i in range(len(rows))]
        return [[v * scale for v in row] for row, scale in zip(rows, scales)], scales

    def observations(self):
        current=[v/self.maze.sensor_range for v in self.sensors()]
        memory, _ = self.input_memory()
        return current+[v for row in memory for v in row]+[0.]*(self.memory_row_width*(self.history_capacity-len(self.memory)))

    def apply_outputs(self,values):
        if len(values)!=len(self.output_values) or any(not math.isfinite(v) for v in values) or self.done:
            raise ValueError('Expected finite movement outputs matching the episode encoding')
        action = decode_bits(values) if self.output_encoding == 'bits2' else MOVES[max(range(4),key=lambda i:values[i])]
        self.output_values=list(values)
        if self.action_memory_steps:
            # The chosen action becomes memory only AFTER the policy has chosen it.
            # Every choice is stored, including attempts at blocked movement.
            self.landmark_signal = False
            self.memory_written = True
            self.memory.append(CHOICE_BITS[action])
            self.memory = self.memory[-self.action_memory_steps:]
            return self.step(action)
        self.landmark_signal=self.landmark_kind() is not None
        position=self.x,self.y
        self.memory_written=self.landmark_signal and (self.choice_memory or position not in self.registered)
        if self.memory_written:
            # Store after choosing an action, so current observation is not duplicated
            # as a new historical entry in that decision's input.
            if self.choice_memory and position in self.registered:
                # Refresh the last observed view AND its choice in the same orientation.
                index = self.memory_places.index(position)
                self.memory.pop(index)
                self.memory_places.pop(index)
            if len(self.memory)>=self.history_capacity:
                raise RuntimeError('History capacity invariant violated')
            row = tuple(v/self.maze.sensor_range for v in self.sensors())
            if self.choice_memory:
                row += CHOICE_BITS[action]
                self.memory_places.append(position)
            self.memory.append(row)
            self.registered.add(position)
        return self.step(action)

    def snapshot(self):
        state=super().snapshot()
        memory, scales = self.input_memory()
        state.update(history_capacity=self.history_capacity,landmark_signal=self.landmark_signal,
                     memory=memory, memory_scales=scales, sensor_angles=list(self.sensor_angles),
                     memory_order='newest_first' if self.newest_first else 'oldest_first')
        state['history_action_memory_steps'] = self.action_memory_steps
        state['history_choice_memory'] = self.choice_memory
        state['memory_row_width'] = self.memory_row_width
        state['output_encoding'] = self.output_encoding
        if self.output_encoding == 'bits2':
            state['output_bits'] = [int(v > 0) for v in self.output_values]
        return state
