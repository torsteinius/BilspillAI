"""Two sensor heights, three local 2-D layers and eight decision layers."""
from .local_vision import LocalVisionNetwork
from .network import NeuralNetwork

RAYS=61
ARCHITECTURE=(366,488,488,488,64,64,48,32,24,16,8,4,2)
MODEL_TYPE='two_height_laser_local_v1'

class LaserVisionNetwork(LocalVisionNetwork):
    def __init__(self,architecture=ARCHITECTURE,*,seed=None):
        if tuple(architecture[:-1])!=ARCHITECTURE[:-1] or architecture[-1] not in (1,2):
            raise ValueError('Expected two-height 61-ray architecture')
        NeuralNetwork.__init__(self,architecture,seed=seed)
        self.sectors=RAYS;self.links=[]
        for layer,(a,b) in enumerate(zip(architecture,architecture[1:])):
            if layer<3:
                channels=a//(2*RAYS)
                # Row-major height, then ray, then feature. No angular wraparound.
                self.links.append([[((h*RAYS+r)*channels+c)
                    for h in range(2) for r in range(max(0,(n//4)%RAYS-1),min(RAYS,(n//4)%RAYS+2))
                    for c in range(channels)] for n in range(b)])
            else:self.links.append([list(range(a)) for _ in range(b)])
        self.weight_count=sum(len(row)+1 for layer in self.links for row in layer)
        self.weights=[0.]*self.weight_count
        self.metadata.update(model_type=MODEL_TYPE,local_layers=3,sensor_heights=[.5,3.],rays_per_height=RAYS,
            local_radius=1,local_dimensions=['height','angle'],sector_channels=[3,4,4,4],
            decision_hidden=list(architecture[4:-1]),radar_mode='laser2',observation_version='laser2_distance_closing_echo_v1')
