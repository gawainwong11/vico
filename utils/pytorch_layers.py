import torch
import torch.nn as nn
import torch.nn.init as init
import numpy as np


class Identity(nn.Module):
    def __init__(self):
        super(Identity,self).__init__()

    def forward(self,x):
        return x


def get_activation(name):
    if name=='ReLU':
        return nn.ReLU(inplace=True)
    elif name=='Tanh':
        return nn.Tanh()
    elif name=='Identity':
        return Identity()
    elif name=='Sigmoid':
        return nn.Sigmoid()
    elif name=='LeakyReLU':
        return nn.LeakyReLU(0.2,inplace=True)
    else:
        assert(False), 'Not Implemented'


def create_mlp(const):
    out_activation = get_activation(const['out_activation'])
    activation = get_activation(const['activation'])
    
    if 'drop_prob' in const:
        drop_prob = const['drop_prob']
    else:
        drop_prob = 0

    if 'out_drop_prob' in const:
        out_drop_prob = const['out_drop_prob']
    else:
        out_drop_prob = 0

    mlp = MLP(
        in_dim=const['in_dim'],
        out_dim=const['out_dim'],
        out_activation=out_activation,
        activation=activation,
        layer_units=const['layer_units'],
        use_out_bn=const['use_out_bn'],
        use_bn=const['use_bn'],
        drop_prob=drop_prob,
        out_drop_prob=out_drop_prob)
    return mlp


class MLP(nn.Module):
    def __init__(
            self,
            in_dim,
            out_dim,
            out_activation,
            layer_units=[],
            activation=nn.ReLU(inplace=True),
            use_out_bn=True,
            use_bn=True,
            drop_prob=0,
            out_drop_prob=0):
        super(MLP,self).__init__()
        self.layers = nn.ModuleList()
        in_units = in_dim 
        for num_units in layer_units:
            out_units = num_units
            fc_layer = self.linear_with_bn_and_activations(
                in_units,
                out_units,
                activation,
                use_bn)
            self.layers.append(fc_layer)
            if drop_prob > 0:
                self.layers.append(nn.Dropout(p=drop_prob))
            in_units = out_units

        fc_layer = self.linear_with_bn_and_activations(
            in_units,
            out_dim,
            out_activation,
            use_out_bn)
        self.layers.append(fc_layer)
        if out_drop_prob > 0:
            self.layers.append(nn.Dropout(p=out_drop_prob))

    def linear_with_bn_and_activations(
            self,
            in_dim,
            out_dim,
            activation,
            use_bn=True):
        linear = nn.Linear(in_dim,out_dim)
        if use_bn:
            bn = nn.BatchNorm1d(out_dim)
            block = nn.Sequential(linear,bn,activation)
        else:
            block = nn.Sequential(linear,activation)
            
        return block

    def forward(self,x):
        for layer in self.layers:
            x = layer(x)

        return x


class LossProgressMonitor():
    def __init__(self,window=1000,delta=1e-4,smoothness=0.9):
        assert(window >= 2)
        self.window = window
        self.delta = delta
        self.smoothness = smoothness
        self.ema = None
        self.deque = deque()

    def add_loss(self,loss):
        if self.ema is None:
            self.ema = loss
        else:
            self.ema = self.smoothness*self.ema + \
                (1-self.smoothness)*loss 
        
        self.deque.append(self.ema)
        if len(self.deque) > self.window:
            self.deque.popleft()

    def measure_progress(self):
        if len(self.deque) < 2:
            return np.Inf
        else:
            return self.deque[0]-self.deque[-1]

    def sufficient_progress(self):
        progress = self.measure_progress()
        is_sufficient = False
        if len(self.deque) < self.window:
            is_sufficient = True 
        else:
            is_sufficient = progress > self.delta
        return is_sufficient, progress


def adjust_learning_rate(optimizer, init_lr, epoch, decay_by=0.2, decay_every=10):
    """Sets the learning rate to the initial LR decayed by 10 every 30 epochs"""
    lr = init_lr * (decay_by ** (epoch // decay_every))
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr


def set_learning_rate(optimizer, lr):
    """Sets the new learning rate"""
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr