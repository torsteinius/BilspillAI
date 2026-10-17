import mlx.core as mx
import mlx.nn as nn


class JunctionDetector(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(8,32),nn.Tanh(),nn.Linear(32,16),nn.Tanh(),nn.Linear(16,1))

    def __call__(self, rays):
        return mx.sigmoid(self.layers(rays)[...,0])
