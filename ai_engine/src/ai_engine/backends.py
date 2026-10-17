import time

class MLXDenseBackend:
    """Explicit Apple GPU backend with reusable device-resident weights."""
    name = 'mlx-gpu'
    def __init__(self):
        import mlx.core as mx
        if not mx.metal.is_available():
            raise RuntimeError('Apple Metal GPU is unavailable; mlx-gpu cannot start')
        self.mx, self.device = mx, mx.gpu
        started = time.perf_counter()
        with mx.stream(self.device):
            mx.eval(mx.array([0.], dtype=mx.float32))
        self.probe_ms = (time.perf_counter()-started)*1000

    def prepare(self, architecture, populations):
        mx = self.mx
        with mx.stream(self.device):
            packed = mx.array(populations, dtype=mx.float32)
            layers, offset = [], 0
            for inputs, outputs in zip(architecture, architecture[1:]):
                size = (inputs+1)*outputs
                layer = packed[:,offset:offset+size].reshape(-1,outputs,inputs+1)
                layers.append((mx.swapaxes(layer[:,:,:-1],-1,-2),layer[:,None,:,-1]))
                offset += size
            mx.eval(layers)
        return layers

    def predict_prepared(self, layers, observations):
        mx = self.mx
        started = time.perf_counter()
        with mx.stream(self.device):
            values = mx.array(observations,dtype=mx.float32)
            for weights,bias in layers:
                values = mx.tanh(values @ weights + bias)
            mx.eval(values)
            result = values.tolist()
        return result, (time.perf_counter()-started)*1000

    def predict_indexed(self, layers, indexes, inputs):
        """Group samples by candidate, reusing its weights without a copy per bot."""
        mx = self.mx
        started = time.perf_counter()
        groups = {}
        for position, candidate in enumerate(indexes):
            groups.setdefault(candidate, []).append(position)
        with mx.stream(self.device):
            pending = []
            for candidate, positions in groups.items():
                values = mx.array([inputs[i] for i in positions], dtype=mx.float32)
                for weights,bias in layers:
                    values = mx.tanh(values @ weights[candidate] + bias[candidate,0])
                pending.append((positions, values))
            mx.eval([values for _,values in pending])
            result = [None]*len(inputs)
            for positions, values in pending:
                for i, output in zip(positions, values.tolist()):
                    result[i] = output
        return result, (time.perf_counter()-started)*1000

    def predict(self, architecture, populations, observations):
        started = time.perf_counter()
        result, _ = self.predict_prepared(self.prepare(architecture, populations), observations)
        return result, (time.perf_counter()-started)*1000
