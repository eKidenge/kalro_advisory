"""
PINN network architecture.

A feed-forward MLP that predicts multiple agronomic outputs from
climate + soil + crop features. Used inside the training loop where
physics losses are added to the data loss.
"""
import torch
import torch.nn as nn


class PINNNetwork(nn.Module):
    """
    Feed-forward network with configurable hidden layers and activation.
    Input features and output targets are defined at model-config time
    (on PINNModel.input_features / PINNModel.output_targets).
    """

    ACTIVATIONS = {
        'relu': nn.ReLU,
        'tanh': nn.Tanh,
        'sigmoid': nn.Sigmoid,
        'gelu': nn.GELU,
        'leaky_relu': nn.LeakyReLU,
    }

    def __init__(self, n_inputs, n_outputs, hidden_layers=None, activation='tanh'):
        super().__init__()

        if hidden_layers is None:
            hidden_layers = [64, 64, 32]

        act_cls = self.ACTIVATIONS.get(activation, nn.Tanh)

        layers = []
        prev = n_inputs
        for h in hidden_layers:
            layers.append(nn.Linear(prev, h))
            layers.append(act_cls())
            prev = h
        layers.append(nn.Linear(prev, n_outputs))

        self.net = nn.Sequential(*layers)
        self.n_inputs = n_inputs
        self.n_outputs = n_outputs

    def forward(self, x):
        return self.net(x)


def build_network_from_model(pinn_model):
    """
    Given a pinn_engine.models.PINNModel instance, construct the
    matching PyTorch network.
    """
    n_inputs = len(pinn_model.input_features or [])
    n_outputs = len(pinn_model.output_targets or [])

    if n_inputs == 0 or n_outputs == 0:
        raise ValueError(
            "PINNModel must have non-empty input_features and output_targets."
        )

    hidden = pinn_model.hidden_layers or [64, 64, 32]

    return PINNNetwork(
        n_inputs=n_inputs,
        n_outputs=n_outputs,
        hidden_layers=hidden,
        activation=pinn_model.activation or 'tanh',
    )
