"""
PINN engine — machine learning layer.

This package contains the actual neural-network code: architecture,
physics loss functions, feature extraction, training loop, and inference.

The Django models in apps.pinn_engine.models wrap this layer so that
training runs and inferences can be scheduled, persisted, and audited.
"""

__all__ = [
    'network',
    'physics',
    'features',
    'trainer',
    'inference',
]
