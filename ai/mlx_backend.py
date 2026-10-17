"""Optional batched dense network inference on Apple Metal via MLX.

Weights retain the original JSON layout. Environments and evolutionary mutations
stay on CPU; all candidates and mazes share a GPU forward pass per timestep.
"""
class BatchedNetwork:
    def __init__(self, architecture, populations, device='gpu'):
        import mlx.core as mx
        self.mx = mx
        if device == 'gpu' and not mx.metal.is_available():
            raise RuntimeError('Apple Metal GPU is unavailable; use the CPU backend')
        self.device = mx.gpu if device == 'gpu' else mx.cpu
        self.layers = []
        with mx.stream(self.device):
            weights = mx.array(populations, dtype=mx.float32)
            offset = 0
            for inputs, outputs in zip(architecture, architecture[1:]):
                count = (inputs + 1) * outputs
                layer = weights[:, offset:offset+count].reshape(-1, outputs, inputs+1)
                self.layers.append((mx.swapaxes(layer[:, :, :-1], -1, -2), layer[:, None, :, -1]))
                offset += count
            mx.eval(self.layers)

    def forward(self, observations):
        mx = self.mx
        with mx.stream(self.device):
            values = mx.array(observations, dtype=mx.float32)
            for weights, bias in self.layers:
                values = mx.tanh(values @ weights + bias)
            mx.eval(values)
            return values.tolist()
