"""MLX networks: perception, recurrent memory, and action selection."""
import mlx.core as mx
import mlx.nn as nn

EVENT_SIZE = 15  # 8 perceived features, previous action(4), displacement(2), turn(1)
HIDDEN = 256
MAX_EVENTS = 67


class Perception(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(8, 32), nn.Tanh(), nn.Linear(32, 32),
                                    nn.Tanh(), nn.Linear(32, 8))

    def __call__(self, rays):
        raw = self.layers(rays)
        # Four probabilities of open adjacent cells and four normalized lengths.
        return mx.sigmoid(raw)


class Memory(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = nn.LSTM(EVENT_SIZE, HIDDEN)
        # Indexed readout: at test time only the final recurrent state is available.
        self.recall = nn.Linear(HIDDEN, MAX_EVENTS * 4)

    def __call__(self, events, hidden=None, cell=None):
        return self.lstm(events, hidden, cell)

    def recall_logits(self, final_hidden):
        return self.recall(final_hidden).reshape(-1, MAX_EVENTS, 4)


class Decision(nn.Module):
    def __init__(self):
        super().__init__()
        # A learned situation-dependent compact readout of the memory.
        self.read = nn.Linear(HIDDEN + 8, 32)
        self.policy = nn.Sequential(nn.Linear(32 + 8 + 8 + 4, 64), nn.Tanh(), nn.Linear(64, 4))

    def __call__(self, rays, perceived, hidden, previous):
        context = mx.tanh(self.read(mx.concatenate([hidden, perceived], axis=-1)))
        return self.policy(mx.concatenate([rays, perceived, context, previous], axis=-1))
