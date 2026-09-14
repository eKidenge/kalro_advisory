"""
PINN training loop.

Given a TrainingRun row, this trains a PINNNetwork on the available
data (historical trials + synthetic physics samples) and writes
metrics back to the ModelMetric table.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from django.utils import timezone

from apps.pinn_engine.ml.network import build_network_from_model, save_network
from apps.pinn_engine.ml.physics import composite_physics_loss
from apps.pinn_engine.ml.features import (
    FEATURE_RANGES,
    feature_index_map,
    output_index_map,
)

logger = logging.getLogger(__name__)


# ==================================================================
# Synthetic sample generation
# ==================================================================
def generate_synthetic_batch(
    feature_names: list[str],
    output_names: list[str],
    n_samples: int = 256,
    seed: Optional[int] = None,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Generate physically plausible (X, y) samples from the FEATURE_RANGES
    and simple crop-response curves.

    This gives the network something to learn from before real training
    data is wired in. Replace with real data in a later milestone.
    """
    rng = np.random.default_rng(seed)

    X = rng.random((n_samples, len(feature_names)), dtype=np.float32)

    # Target: a smooth function of the inputs.
    # For yield_kg_ha, we use rainfall + soil N − thermal penalty.
    def _idx(name):
        try:
            return feature_names.index(name)
        except ValueError:
            return None

    def _out_idx(name):
        try:
            return output_names.index(name)
        except ValueError:
            return None

    Y = np.zeros((n_samples, len(output_names)), dtype=np.float32)

    rain_i = _idx('rainfall')
    soil_n_i = _idx('soil_n')
    soil_p_i = _idx('soil_p')
    temp_i = _idx('temp_max')
    base_i = _idx('base_temp')

    for j, oname in enumerate(output_names):
        if oname in ('yield_kg_ha', 'yield'):
            y = np.full(n_samples, 0.5, dtype=np.float32)
            if rain_i is not None:
                # yield grows with rainfall up to a point
                y += 0.3 * X[:, rain_i]
            if soil_n_i is not None:
                y += 0.15 * X[:, soil_n_i]
            if soil_p_i is not None:
                y += 0.1 * X[:, soil_p_i]
            if temp_i is not None and base_i is not None:
                # thermal penalty
                y -= 0.2 * np.maximum(0.0, X[:, temp_i] - X[:, base_i])
            Y[:, j] = np.clip(y, 0.0, 1.0)

        elif oname == 'n_uptake':
            y = np.full(n_samples, 0.3, dtype=np.float32)
            if soil_n_i is not None:
                y += 0.5 * X[:, soil_n_i]
            Y[:, j] = np.clip(y, 0.0, 1.0)

        elif oname == 'water_stress':
            y = np.full(n_samples, 0.4, dtype=np.float32)
            if rain_i is not None:
                y -= 0.6 * X[:, rain_i]
            if temp_i is not None:
                y += 0.3 * X[:, temp_i]
            Y[:, j] = np.clip(y, 0.0, 1.0)

        else:
            # default: mild function of the first feature
            Y[:, j] = np.clip(0.5 + 0.2 * (X[:, 0] - 0.5), 0.0, 1.0)

    return torch.from_numpy(X), torch.from_numpy(Y)


# ==================================================================
# Constraint payloads — extract from physics_constraints M2M
# ==================================================================
def constraints_to_payload(pinn_model) -> list[dict]:
    """
    Pull the physics constraints attached to the PINNModel into a
    plain list of dicts the physics module understands.
    """
    out = []
    for c in pinn_model.physics_constraints.filter(is_active=True):
        out.append({
            'kind': c.kind,
            'weight': float(c.weight),
            'name': c.name,
        })
    return out


# ==================================================================
# Training loop
# ==================================================================
def train_pinn(
    training_run,
    progress_callback=None,
) -> dict:
    """
    Execute a full training run.

    Args:
        training_run: pinn_engine.models.TrainingRun instance
        progress_callback: optional callable(epoch, metrics_dict)

    Returns:
        dict of final metrics
    """
    from apps.pinn_engine.models import ModelMetric

    pinn_model = training_run.model
    feature_names = list(pinn_model.input_features or [])
    output_names  = list(pinn_model.output_targets or [])

    if not feature_names or not output_names:
        raise ValueError(
            "PINNModel must have input_features and output_targets configured."
        )

    # ---- 1. Build network ----
    net = build_network_from_model(pinn_model)
    logger.info("Built network: %s", net.summary())

    # ---- 2. Generate training data ----
    X, Y = generate_synthetic_batch(
        feature_names, output_names,
        n_samples=max(1024, training_run.batch_size * 8),
        seed=training_run.pk,
    )

    # ---- 3. Train / val split ----
    n_total = X.shape[0]
    n_train = int(n_total * float(training_run.train_split))
    X_train, Y_train = X[:n_train], Y[:n_train]
    X_val,   Y_val   = X[n_train:], Y[n_train:]

    # ---- 4. Optimizer + loss ----
    optimizer = torch.optim.Adam(net.parameters(), lr=float(training_run.learning_rate))
    data_loss_fn = nn.MSELoss()

    constraints = constraints_to_payload(pinn_model)
    fmap = feature_index_map(feature_names)
    omap = output_index_map(output_names)
    lambda_physics = float(pinn_model.physics_lambda)

    # ---- 5. Loop ----
    batch_size = training_run.batch_size
    epochs = training_run.epochs
    start_time = time.monotonic()

    best_val = float('inf')
    history = []

    for epoch in range(1, epochs + 1):
        net.train()

        # Shuffle training set each epoch
        perm = torch.randperm(X_train.shape[0])
        X_train_shuf = X_train[perm]
        Y_train_shuf = Y_train[perm]

        epoch_data_loss = 0.0
        epoch_phys_loss = 0.0
        n_batches = 0

        for i in range(0, X_train_shuf.shape[0], batch_size):
            xb = X_train_shuf[i:i + batch_size]
            yb = Y_train_shuf[i:i + batch_size]

            optimizer.zero_grad()
            preds = net(xb)

            # Data loss
            l_data = data_loss_fn(preds, yb)

            # Physics loss
            l_phys, _ = composite_physics_loss(
                preds, xb, constraints, fmap, omap,
            )

            # Composite
            total = l_data + lambda_physics * l_phys

            total.backward()
            optimizer.step()

            epoch_data_loss += float(l_data.item())
            epoch_phys_loss += float(l_phys.item())
            n_batches += 1

        # ---- Validation ----
        net.eval()
        with torch.no_grad():
            val_preds = net(X_val)
            val_loss = float(data_loss_fn(val_preds, Y_val).item())

        avg_data = epoch_data_loss / max(n_batches, 1)
        avg_phys = epoch_phys_loss / max(n_batches, 1)

        metrics = {
            'epoch': epoch,
            'data_loss': avg_data,
            'physics_loss': avg_phys,
            'total_loss': avg_data + lambda_physics * avg_phys,
            'val_loss': val_loss,
            'rmse': val_loss ** 0.5,
            'r2': 1.0 - val_loss,          # rough proxy; refined later
            'physics_residual': avg_phys,
        }
        history.append(metrics)

        # Persist snapshot (every epoch)
        ModelMetric.objects.create(
            model=pinn_model,
            training_run=training_run,
            epoch=epoch,
            data_loss=avg_data,
            physics_loss=avg_phys,
            total_loss=metrics['total_loss'],
            rmse=metrics['rmse'],
            r2=metrics['r2'],
            physics_residual=avg_phys,
        )

        if progress_callback:
            progress_callback(epoch, metrics)

        best_val = min(best_val, val_loss)

    # ---- 6. Save weights ----
    artifact_path = f'/tmp/pinn_model_{pinn_model.pk}_{training_run.pk}.pt'
    save_network(net, artifact_path)
    pinn_model.artifact_path = artifact_path
    pinn_model.status = 'READY'
    pinn_model.metrics = {
        'final_val_loss': best_val,
        'final_rmse': best_val ** 0.5,
        'epochs_trained': epochs,
        'n_parameters': net.n_parameters,
    }
    pinn_model.save(update_fields=['artifact_path', 'status', 'metrics'])

    duration = int(time.monotonic() - start_time)

    return {
        'final_val_loss': best_val,
        'final_rmse': best_val ** 0.5,
        'duration_seconds': duration,
        'history': history[-5:],   # last 5 epochs for logging
    }
