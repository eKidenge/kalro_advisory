"""
PINN network architecture.

A feed-forward MLP that predicts multiple agronomic outputs from
climate + soil + crop features. Used inside the training loop where
physics losses are added to the data loss.

We keep the network deliberately simple — the value comes from the
physics constraints, not from a deep architecture.
"""
from __future__ import annotations

import logging

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


# ==================================================================
# Architecture
# ==================================================================
class PINNNetwork(nn.Module):
    """
    Feed-forward network with configurable hidden layers and activation.

    Input features and output targets are defined at model-config time
    (PINNModel.input_features / PINNModel.output_targets). This class
    just builds the graph.
    """

    ACTIVATIONS = {
        'relu':       nn.ReLU,
        'tanh':       nn.Tanh,
        'sigmoid':    nn.Sigmoid,
        'gelu':       nn.GELU,
        'leaky_relu': nn.LeakyReLU,
        'silu':       nn.SiLU,
        'elu':        nn.ELU,
    }

    def __init__(
        self,
        n_inputs: int,
        n_outputs: int,
        hidden_layers: list[int] | None = None,
        activation: str = 'tanh',
        dropout: float = 0.0,
        batch_norm: bool = False,
    ):
        super().__init__()

        if hidden_layers is None:
            hidden_layers = [64, 64, 32]

        if activation not in self.ACTIVATIONS:
            logger.warning(
                "Unknown activation '%s', falling back to 'tanh'.", activation,
            )
            activation = 'tanh'

        act_cls = self.ACTIVATIONS[activation]

        layers: list[nn.Module] = []
        prev = n_inputs

        for i, h in enumerate(hidden_layers):
            layers.append(nn.Linear(prev, h))

            if batch_norm:
                layers.append(nn.BatchNorm1d(h))

            layers.append(act_cls())

            if dropout and dropout > 0:
                layers.append(nn.Dropout(p=dropout))

            prev = h

        layers.append(nn.Linear(prev, n_outputs))

        self.net = nn.Sequential(*layers)
        self.n_inputs = n_inputs
        self.n_outputs = n_outputs
        self.hidden_layers = list(hidden_layers)
        self.activation = activation

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    # ------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------
    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def summary(self) -> dict:
        return {
            'n_inputs': self.n_inputs,
            'n_outputs': self.n_outputs,
            'hidden_layers': self.hidden_layers,
            'activation': self.activation,
            'n_parameters': self.n_parameters,
        }


# ==================================================================
# Factory — build from a PINNModel row
# ==================================================================
def build_network_from_model(pinn_model) -> PINNNetwork:
    """
    Given a pinn_engine.models.PINNModel instance, construct the
    matching PyTorch network.

    Raises ValueError if the model is not fully configured.
    """
    n_inputs = len(pinn_model.input_features or [])
    n_outputs = len(pinn_model.output_targets or [])

    if n_inputs == 0:
        raise ValueError(
            "PINNModel has no input_features configured — cannot build network."
        )
    if n_outputs == 0:
        raise ValueError(
            "PINNModel has no output_targets configured — cannot build network."
        )

    hidden = pinn_model.hidden_layers or [64, 64, 32]

    return PINNNetwork(
        n_inputs=n_inputs,
        n_outputs=n_outputs,
        hidden_layers=hidden,
        activation=pinn_model.activation or 'tanh',
    )


# ==================================================================
# Persistence
# ==================================================================
def save_network(network: PINNNetwork, path: str) -> None:
    """Save weights + architecture summary to disk."""
    payload = {
        'state_dict': network.state_dict(),
        'config': network.summary(),
    }
    torch.save(payload, path)
    logger.info("Saved network to %s (%d parameters)", path, network.n_parameters)


def load_network(path: str) -> PINNNetwork:
    """Restore a network from a saved checkpoint."""
    payload = torch.load(path, map_location='cpu', weights_only=False)
    cfg = payload['config']

    net = PINNNetwork(
        n_inputs=cfg['n_inputs'],
        n_outputs=cfg['n_outputs'],
        hidden_layers=cfg['hidden_layers'],
        activation=cfg['activation'],
    )
    net.load_state_dict(payload['state_dict'])
    net.eval()
    return net
