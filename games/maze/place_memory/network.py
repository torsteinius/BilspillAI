import mlx.core as mx
import mlx.nn as nn

HIDDEN=256


class PlaceMemory(nn.Module):
    def __init__(self):
        super().__init__()
        self.encode=nn.Linear(8,32)
        self.lstm=nn.LSTM(32,HIDDEN)
        self.read=nn.Sequential(nn.Linear(HIDDEN+8,128),nn.Tanh(),nn.Linear(128,1))

    def step(self,x,write,h,c):
        # Read the OLD state: current observation has not been stored yet.
        logit=self.read(mx.concatenate([x,h],axis=-1))[...,0]
        hs,cs=self.lstm(mx.tanh(self.encode(x))[:,None,:],h,c)
        h=mx.where(write[:,None],hs[:,0],h)
        c=mx.where(write[:,None],cs[:,0],c)
        return logit,h,c

    def __call__(self,x,writes,reset_each_query=False,shuffle_read=False):
        h=mx.zeros((x.shape[0],HIDDEN));c=mx.zeros_like(h);logits=[]
        for i in range(x.shape[1]):
            if reset_each_query:
                h=mx.zeros_like(h);c=mx.zeros_like(c)
            previous_h=h
            logit,h,c=self.step(x[:,i],writes[:,i],h,c)
            if shuffle_read:
                logit=self.read(mx.concatenate([x[:,i],mx.roll(previous_h,1,axis=0)],axis=-1))[...,0]
            logits.append(logit)
        return mx.stack(logits,axis=1)
