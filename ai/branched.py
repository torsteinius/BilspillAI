"""Separate present/history encoders, followed by a shared decision network."""
import math
import random
from ai.network import NeuralNetwork

BRANCHES = ((4, 4, 4, 4), (256, 64, 16, 4), (8, 8, 2))
MODEL_TYPE = 'present_history_branches_v1'

class BranchedNetwork(NeuralNetwork):
    def __init__(self, architecture=(260, 2), *, seed=None):
        if tuple(architecture) != (260, 2):
            raise ValueError('Branched network expects 4 present and 256 history inputs')
        super().__init__(architecture, seed=seed)
        self.weight_count = sum((a+1)*b for branch in BRANCHES for a,b in zip(branch,branch[1:]))
        self.weights = [0.] * self.weight_count
        self.metadata.update(model_type=MODEL_TYPE, branches=[list(b) for b in BRANCHES])

    def randomize(self):
        rng=random.Random(self.seed)
        self.weights=[rng.gauss(0,1/math.sqrt(a)) for branch in BRANCHES
                      for a,b in zip(branch,branch[1:]) for _ in range((a+1)*b)]

    def forward(self, inputs, weights=None):
        weights=self.weights if weights is None else weights
        if len(inputs)!=260 or len(weights)!=self.weight_count:
            raise ValueError('Inputs and weights must match branched architecture')
        offset=0
        def branch(values, sizes):
            nonlocal offset
            for a,b in zip(sizes,sizes[1:]):
                values=[math.tanh(sum(weights[offset+n*(a+1)+i]*v for i,v in enumerate(values))
                                  +weights[offset+n*(a+1)+a]) for n in range(b)]
                offset+=(a+1)*b
            return values
        present=branch(inputs[:4],BRANCHES[0])
        history=branch(inputs[4:],BRANCHES[1])
        return branch(present+history,BRANCHES[2])

    def freeze_unused(self,candidate,champion,used):
        # Only first-layer history columns without observations are frozen.
        offset=sum((a+1)*b for a,b in zip(BRANCHES[0],BRANCHES[0][1:]))
        for n in range(64):
            a=offset+n*257+max(0,used-4);b=offset+n*257+256
            candidate[a:b]=champion[a:b]


from ai_service.generic import MLXDenseBackend

class MLXBranchedBackend(MLXDenseBackend):
    def prepare(self, architecture, populations):
        mx=self.mx
        result=[];offset=0
        for branch in BRANCHES:
            count=sum((a+1)*b for a,b in zip(branch,branch[1:]))
            result.append(super().prepare(branch,[p[offset:offset+count] for p in populations]))
            offset+=count
        if any(len(p)!=offset for p in populations):raise ValueError('Invalid branched weights')
        return result

    def predict_indexed(self,layers,indexes,inputs,normalization=None):
        if normalization:raise ValueError('Branched model uses plain tanh')
        import time
        started=time.perf_counter();mx=self.mx
        groups={}
        for i,candidate in enumerate(indexes):groups.setdefault(candidate,[]).append(i)
        with mx.stream(self.device):
            pending=[]
            for candidate,positions in groups.items():
                values=mx.array([inputs[i] for i in positions],dtype=mx.float32)
                def branch(v,weights):
                    for w,b in weights:v=mx.tanh(v@w[candidate]+b[candidate,0])
                    return v
                present=branch(values[:,:4],layers[0]);history=branch(values[:,4:],layers[1])
                pending.append((positions,branch(mx.concatenate([present,history],axis=-1),layers[2])))
            mx.eval([v for _,v in pending]);result=[None]*len(inputs)
            for positions,values in pending:
                for i,v in zip(positions,values.tolist()):result[i]=v
        return result,(time.perf_counter()-started)*1000
