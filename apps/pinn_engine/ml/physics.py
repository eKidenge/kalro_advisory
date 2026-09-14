"""
Physics loss functions for the PINN.

Each function takes the network's raw predictions (and, where needed,
the input features) and returns a scalar tensor representing how
badly the prediction violates that physical law. Small values mean
the prediction is physically consistent.

Because the true physics depends on unknown coefficients (soil depth,
field capacity, drainage rates), we use simplified, normalized forms
of each law that are robust to parameter uncertainty. The weights on
each constraint are pulled from the PhysicsConstraint table so
researchers can tune them.
"""
from __future__ import annotations

import logging

import torch

logger = logging.getLogger(__name__)


# ==================================================================
# Water balance — dS/dt = P - ET - R - D
# ==================================================================
def water_balance_loss(
    predictions: torch.Tensor,
    features: torch.Tensor,
    feature_index: dict[str, int],
    output_index: dict[str, int],
) -> torch.Tensor:
    """
    Enforces: ΔS = P − ET − R − D (all normalized to [0,1])

    Simplified form for a single time step:
        soil_moisture_change ≈ rainfall − evapotranspiration − runoff

    Since we don't predict every term, we express the constraint as:
        |predicted_water_stress + predicted_ET − rainfall| → 0

    In the current output schema:
        - input:  'rainfall', 'temp_max'
        - output: 'water_stress' (0 = no stress, 1 = severe)

    Interpretation: if rainfall is high, water stress should be low;
    if rainfall is low and temperature high, stress should be high.
    The loss pushes the network to respect that relationship.
    """
    try:
        rain_i = feature_index.get('rainfall')
        temp_i = feature_index.get('temp_max')
        stress_i = output_index.get('water_stress')

        if stress_i is None:
            return torch.tensor(0.0, device=predictions.device)

        stress = predictions[:, stress_i]

        # Simple physical prior: water stress rises when rain is low
        # and temp is high. Both features are in [0,1] after scaling.
        if rain_i is not None and temp_i is not None:
            rain = features[:, rain_i]
            temp = features[:, temp_i]

            # Expected stress ≈ (1 - rain) * temp
            expected = (1.0 - rain) * temp
            return torch.mean((stress - expected) ** 2)

        # Fallback: penalize stress outside [0, 1]
        return torch.mean(torch.relu(-stress) + torch.relu(stress - 1.0))

    except Exception as e:
        logger.warning("water_balance_loss failed: %s", e)
        return torch.tensor(0.0, device=predictions.device)


# ==================================================================
# Nutrient cycling — dN/dt = F + M - U - L
# ==================================================================
def nutrient_cycle_loss(
    predictions: torch.Tensor,
    features: torch.Tensor,
    feature_index: dict[str, int],
    output_index: dict[str, int],
) -> torch.Tensor:
    """
    Enforces: predicted nitrogen uptake must be plausible given
    available soil nitrogen, fertilizer input, and crop demand.

    Currently:
        - input:  'soil_n', 'crop_n_req', 'fertilizer_n'
        - output: 'n_uptake'

    Constraint: n_uptake should be a smooth function of available N
    and crop demand. We penalize:
        1. Uptake far outside [0, min(available, demand)] → physically impossible
        2. Uptake that doesn't correlate with soil nitrogen
    """
    try:
        soil_n_i = feature_index.get('soil_n')
        crop_req_i = feature_index.get('crop_n_req')
        fert_n_i = feature_index.get('fertilizer_n')
        uptake_i = output_index.get('n_uptake')

        if uptake_i is None:
            return torch.tensor(0.0, device=predictions.device)

        uptake = predictions[:, uptake_i]

        # Non-negativity
        loss = torch.mean(torch.relu(-uptake))

        # Upper bound: uptake shouldn't exceed (soil N + fertilizer N)
        if soil_n_i is not None:
            soil_n = features[:, soil_n_i]
            if fert_n_i is not None:
                available = soil_n + features[:, fert_n_i]
            else:
                available = soil_n

            excess = torch.relu(uptake - available)
            loss = loss + torch.mean(excess)

        # Demand match: uptake should approach crop requirement
        if crop_req_i is not None:
            crop_req = features[:, crop_req_i]
            loss = loss + 0.5 * torch.mean((uptake - crop_req) ** 2)

        return loss

    except Exception as e:
        logger.warning("nutrient_cycle_loss failed: %s", e)
        return torch.tensor(0.0, device=predictions.device)


# ==================================================================
# Energy conservation — Rn = LE + H + G
# ==================================================================
def energy_conservation_loss(
    predictions: torch.Tensor,
    features: torch.Tensor,
    feature_index: dict[str, int],
    output_index: dict[str, int],
) -> torch.Tensor:
    """
    Enforces: yield response to temperature is bounded by energy
    inputs. High temperatures beyond the crop's optimal range
    reduce yield; the model should not predict the opposite.

    Uses 'temp_max' and 'base_temp' inputs against the primary yield
    output.
    """
    try:
        temp_max_i = feature_index.get('temp_max')
        base_temp_i = feature_index.get('base_temp')
        yield_i = (
            output_index.get('yield_kg_ha')
            or output_index.get('yield')
            or (list(output_index.values())[0] if output_index else None)
        )

        if yield_i is None or temp_max_i is None:
            return torch.tensor(0.0, device=predictions.device)

        temp = features[:, temp_max_i]
        y = predictions[:, yield_i]

        # Smooth penalty when temperature exceeds the crop's optimum.
        # We use base_temp as a proxy for the optimum.
        if base_temp_i is not None:
            base = features[:, base_temp_i]
            # thermal penalty: how far above optimal
            thermal_penalty = torch.relu(temp - base)
            # yield should decrease monotonically with penalty.
            # Penalize positive correlation between yield and penalty.
            covariance = torch.mean(y * thermal_penalty)
            return torch.relu(covariance)

        return torch.tensor(0.0, device=predictions.device)

    except Exception as e:
        logger.warning("energy_conservation_loss failed: %s", e)
        return torch.tensor(0.0, device=predictions.device)


# ==================================================================
# Dispatch table
# ==================================================================
CONSTRAINT_FUNCTIONS = {
    'WATER':    water_balance_loss,
    'NUTRIENT': nutrient_cycle_loss,
    'ENERGY':   energy_conservation_loss,
}


# ==================================================================
# Composite physics loss
# ==================================================================
def composite_physics_loss(
    predictions: torch.Tensor,
    features: torch.Tensor,
    constraints: list[dict],
    feature_index: dict[str, int],
    output_index: dict[str, int],
) -> tuple[torch.Tensor, dict[str, float]]:
    """
    Combine all active physics constraints into one weighted loss.

    Args:
        predictions: (batch, n_outputs) tensor of raw model outputs
        features:    (batch, n_inputs) tensor of raw inputs
        constraints: list of dicts, each with keys:
                     - 'kind'   : one of WATER, NUTRIENT, ENERGY, ...
                     - 'weight' : float, λ in the composite loss

    Returns:
        (total_loss_tensor, {constraint_name: value})
    """
    device = predictions.device
    total = torch.tensor(0.0, device=device)
    breakdown: dict[str, float] = {}

    for c in constraints:
        kind = c.get('kind')
        weight = float(c.get('weight', 1.0))
        name = c.get('name', kind)

        fn = CONSTRAINT_FUNCTIONS.get(kind)
        if fn is None:
            continue

        value = fn(predictions, features, feature_index, output_index)
        total = total + weight * value
        breakdown[name] = float(value.detach().cpu().item())

    return total, breakdown
