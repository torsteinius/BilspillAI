import time

class MLXDenseBackend:
    """Explicit Apple GPU backend. mx.eval makes reported wall time meaningful."""
    name = 'mlx-gpu'
    def __init__(self):
        import mlx.core as mx
        if not mx.metal.is_available(): raise RuntimeError('Apple Metal GPU is unavailable; mlx-gpu cannot start')
        self.mx, self.device = mx, mx.gpu
        started=time.perf_counter()
        with mx.stream(self.device): mx.eval(mx.array([0.], dtype=mx.float32))
        self.probe_ms=(time.perf_counter()-started)*1000
    def predict(self, architecture, populations, observations):
        """Return [candidate][sample][output], synchronously evaluated on GPU."""
        mx=self.mx; started=time.perf_counter()
        with mx.stream(self.device):
            packed=mx.array(populations, dtype=mx.float32); layers=[]; offset=0
            for inputs, outputs in zip(architecture, architecture[1:]):
                size=(inputs+1)*outputs
                layer=packed[:,offset:offset+size].reshape(-1,outputs,inputs+1)
                layers.append((mx.swapaxes(layer[:,:,:-1],-1,-2),layer[:,None,:,-1])); offset+=size
            values=mx.array(observations,dtype=mx.float32)
            for weights,bias in layers: values=mx.tanh(values @ weights + bias)
            mx.eval(values); result=values.tolist()
        return result, (time.perf_counter()-started)*1000
