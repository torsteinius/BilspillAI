"""Separate per-policy gradient batches; MLX is optional and imported on demand."""
import math

_GPU_ENGINES={}


def gradients(policy, rows):
    if policy.batch_backend=='rust' or len(rows)<50:
        from ai.rust_backend import native_module
        return native_module().policy_batch(policy.actor._native,policy.baseline._native,
            policy.actor.weights,policy.baseline.weights,rows)
    if policy.batch_engine is None:
        key=tuple(policy.actor.architecture)
        if key not in _GPU_ENGINES:_GPU_ENGINES[key]=MlxGradients(policy.actor,policy.baseline)
        policy.batch_engine=_GPU_ENGINES[key]
    return policy.batch_engine(policy.actor.weights,policy.baseline.weights,rows)


class MlxGradients:
    def __init__(self,actor,baseline):
        import mlx.core as mx
        if not mx.metal.is_available():raise RuntimeError('Metal GPU unavailable')
        self.mx=mx
        def layout(net):
            result=[];off=0
            for size,layer in zip(net.architecture,net.links):
                indices=[];masks=[];bias=[]
                for row in layer:
                    lookup={j:off+k for k,j in enumerate(row)}
                    indices.append([lookup.get(j,0) for j in range(size)])
                    masks.append([float(j in lookup) for j in range(size)])
                    bias.append(off+len(row));off+=len(row)+1
                result.append((mx.array(indices),mx.array(masks),mx.array(bias)))
            return result
        with mx.stream(mx.gpu):
            actor_layout=layout(actor);base_layout=layout(baseline)
            def forward(w,x,layers):
                for i,(indices,mask,bias) in enumerate(layers):
                    x=x@(w[indices]*mask).T+w[bias]
                    if i<len(layers)-1:x=mx.tanh(x)
                return x
            def objective(aw,bw,x,samples,behavior,reward,incremental):
                means=forward(aw,x,actor_layout);base=forward(bw,x,base_layout)[:,0]
                log_ratio=mx.sum((samples-behavior)**2-(samples-means)**2,axis=1)/(2*.15**2)
                ratio=mx.exp(mx.clip(log_ratio,-20.,math.log(2.)))
                advantage=reward/50.-mx.where(incremental,0.,base)
                actor_loss=mx.stop_gradient(ratio*advantage)*(-mx.sum((samples-means)**2,axis=1)/(2*.15**2))
                baseline_loss=mx.stop_gradient(advantage)*base
                return mx.mean(actor_loss+baseline_loss)
            self.compute=mx.compile(mx.grad(objective,argnums=(0,1)))
    def __call__(self,aw,bw,rows):
        mx=self.mx
        with mx.stream(mx.gpu):
            x,samples,behavior,reward,incremental=zip(*rows)
            ag,bg=self.compute(mx.array(aw,dtype=mx.float32),mx.array(bw,dtype=mx.float32),
                mx.array(x,dtype=mx.float32),mx.array(samples,dtype=mx.float32),mx.array(behavior,dtype=mx.float32),mx.array(reward,dtype=mx.float32),mx.array(incremental))
            mx.eval(ag,bg)
            return ag.tolist(),bg.tolist()
