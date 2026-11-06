"""Three local sector layers, five dense decision layers, then action outputs."""
import math
import random
from .network import NeuralNetwork

MODEL_TYPE='sector_local_vision_v1'
DEFAULT=(30,60,60,60,32,24,16,8,4,2)
FOCUSED=(60,120,120,120,32,24,16,8,4,2)

class LocalVisionNetwork(NeuralNetwork):
    def __init__(self,architecture=DEFAULT,*,seed=None):
        if tuple(architecture[:-1]) not in (DEFAULT[:-1],FOCUSED[:-1]) or architecture[-1] not in (1,2):
            raise ValueError('Expected 15 or 30 sectors, three local layers, five decision layers and 1/2 outputs')
        super().__init__(architecture,seed=seed)
        self.sectors=architecture[0]//2
        self.links=[]
        for layer,(a,b) in enumerate(zip(architecture,architecture[1:])):
            if layer<3:
                channels=a//self.sectors
                self.links.append([[s*channels+c for s in range(max(0,n//4-1),min(self.sectors,n//4+2)) for c in range(channels)] for n in range(b)])
            else:self.links.append([list(range(a)) for _ in range(b)])
        self.weight_count=sum(len(row)+1 for layer in self.links for row in layer)
        self.weights=[0.]*self.weight_count
        self.metadata.update(model_type=MODEL_TYPE,local_layers=3,sector_channels=[2,4,4,4],local_radius=1,decision_hidden=[32,24,16,8,4])

    def set_backend(self,backend):
        if backend not in ('python','rust'):raise ValueError('Unknown backend')
        self.backend=backend
        if backend=='rust':
            from .rust_backend import native_module
            self._native=native_module().LocalNetwork(list(self.architecture),self.links)
        return self

    def randomize(self):
        rng=random.Random(self.seed);self.weights=[]
        for layer in self.links:
            for links in layer:self.weights.extend([rng.gauss(0,1/math.sqrt(len(links))) for _ in links]+[0.])

    def _activations(self,inputs,weights):
        if len(inputs)!=self.architecture[0] or len(weights)!=self.weight_count:raise ValueError('Local network shape mismatch')
        acts=[list(inputs)];offsets=[];off=0
        for l,layer in enumerate(self.links):
            offsets.append(off);out=[]
            for links in layer:
                v=weights[off+len(links)]+sum(weights[off+k]*acts[-1][i] for k,i in enumerate(links))
                out.append(v if l==len(self.links)-1 else math.tanh(v));off+=len(links)+1
            acts.append(out)
        return acts,offsets

    def latent(self,inputs):
        if self.backend=='rust':return self._native.latent(inputs,self.weights)
        return self._activations(inputs,self.weights)[0][-1]

    def gradient(self,inputs,output_index=0):
        if self.backend=='rust':return self._native.gradient(inputs,self.weights,output_index)
        a,offsets=self._activations(inputs,self.weights);g=[0.]*self.weight_count
        delta=[float(i==output_index) for i in range(self.architecture[-1])]
        for l in reversed(range(len(self.links))):
            prev=[0.]*self.architecture[l];off=offsets[l]
            for n,links in enumerate(self.links[l]):
                for k,i in enumerate(links):g[off+k]=delta[n]*a[l][i];prev[i]+=self.weights[off+k]*delta[n]
                g[off+len(links)]=delta[n];off+=len(links)+1
            delta=[v*(1-a[l][i]**2) for i,v in enumerate(prev)] if l else prev
        return a[-1][output_index],g

    def forward(self,inputs,weights=None):
        w=self.weights if weights is None else weights
        if self.backend=='rust':return self._native.forward(inputs,w,False)
        return [math.tanh(v) for v in self._activations(inputs,w)[0][-1]]

    def forward_batch(self,observations,weights=None):
        return [self.forward(x,weights) for x in observations]
