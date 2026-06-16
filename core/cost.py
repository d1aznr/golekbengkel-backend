"""Dynamic cost function using terrain speed models (GLM, Tobler, Naismith).

Supports:
1. GLM Speed Model (Wood et al., 2023):
   v = exp(a + b*phi + c*theta + d*theta^2)
2. Tobler's Hiking Function:
   v = 6 * exp(-3.5 * |s + 0.05|)
3. Naismith's Rule:
   v = 5 * distance / (distance + 8.3333 * max(0, delta_h))

Slope Multiplier:
- Represents task difficulty or load weight (e.g., pushing a motorcycle).
- Scales elevation changes or gradients by a factor (default 3.0 for pushing 2x body weight).
- Applies to all model speed calculations.
"""

import math
from typing import Dict, Union

# GLM Coefficients from Wood et al. (2023) Table 2
GLM_COEFFICIENTS = {
    "paved_road": {
        "a": 1.580,
        "b": -0.00389,
        "c": -0.00726,
        "d": -0.00218,
    },
    "unpaved_road": {
        "a": 1.580,
        "b": -0.00389,
        "c": -0.00965,
        "d": -0.00248,
    },
    "off_road_unknown": {
        "a": 1.536,
        "b": -0.00731,
        "c": -0.00965,
        "d": -0.00187,
    },
    "off_road_light": {
        "a": 1.580,
        "b": -0.00731,
        "c": -0.00965,
        "d": -0.00187,
    },
    "off_road_heavy": {
        "a": 1.443,
        "b": -0.00731,
        "c": -0.00965,
        "d": -0.00187,
    },
}


def scale_slope_deg(slope_deg: float, multiplier: float) -> float:
    """Scale a slope angle in degrees by a gradient multiplier.

    For example, if elevation is multiplied by 3, the gradient (tangent) is 3x.
    """
    if multiplier == 1.0 or slope_deg == 0.0:
        return slope_deg
    scaled_tan = multiplier * math.tan(math.radians(slope_deg))
    # Clip to avoid math domain errors near 90 degrees
    scaled_tan = max(-10.0, min(10.0, scaled_tan))
    return math.degrees(math.atan(scaled_tan))


def get_velocity(
    edge_data: Dict,
    model_type: str = "glm",
    ignore_downhill: bool = False,
    slope_multiplier: float = 3.0,
) -> float:
    """Calculate the effective velocity in km/h based on the selected model and slope multiplier.

    Args:
        edge_data: Dictionary containing edge attributes.
        model_type: Velocity model name ('glm', 'tobler', or 'naismith').
        ignore_downhill: If False, downhill segments (< 0) are set to constant 5.0 km/h.
        slope_multiplier: Elevation/slope multiplier to simulate pushing difficulty.

    Returns:
        Effective velocity in km/h (minimum clamped at 0.1 to avoid division by zero).
    """
    walking_slope = edge_data.get("walking_slope_deg", 0.0)
    distance = edge_data.get("distance", 0.0)
    elev_u = edge_data.get("elevation_u", 0.0)
    elev_v = edge_data.get("elevation_v", 0.0)

    # 1. Apply downhill override if not ignored
    if not ignore_downhill and walking_slope < 0.0:
        return 5.0

    # 2. Select speed model
    model_type_lower = model_type.strip().lower()

    if model_type_lower == "tobler":
        # Tobler's Hiking Function: v = 6 * exp(-3.5 * |s_eff + 0.05|)
        s = (elev_v - elev_u) / distance if distance > 0.0 else 0.0
        s_eff = slope_multiplier * s
        speed = 6.0 * math.exp(-3.5 * abs(s_eff + 0.05))

    elif model_type_lower == "naismith":
        # Naismith's Rule: 5 km/h base speed, adding 1 hour per 600m ascent.
        # delta_h is scaled by the slope_multiplier.
        delta_h = (elev_v - elev_u) * slope_multiplier
        if delta_h > 0.0:
            speed = (5.0 * distance) / (distance + 8.3333 * delta_h)
        else:
            speed = 5.0

    else:  # Default to 'glm'
        hill_slope = edge_data.get("hill_slope_deg", 0.0)
        road_type = edge_data.get("road_type", "paved_road")

        # Scale slopes using the gradient multiplier
        walking_slope_eff = scale_slope_deg(walking_slope, slope_multiplier)
        hill_slope_eff = scale_slope_deg(hill_slope, slope_multiplier)

        # Retrieve coefficients
        coeffs = GLM_COEFFICIENTS.get(road_type, GLM_COEFFICIENTS["paved_road"])
        a = coeffs["a"]
        b = coeffs["b"]
        c = coeffs["c"]
        d = coeffs["d"]

        # Calculate velocity: v = exp(a + b*phi_eff + c*theta_eff + d*theta_eff^2)
        speed = math.exp(
            a + b * hill_slope_eff + c * walking_slope_eff + d * (walking_slope_eff**2)
        )

    # Clamp speed at a minimum of 0.1 km/h to prevent division by zero or negative values
    return max(0.1, speed)


def calculate_cost(
    edge_data: Dict,
    weight_type_or_lambda: Union[str, float, int] = "time",
    model_type: str = "glm",
    ignore_downhill: bool = False,
    slope_multiplier: float = 3.0,
) -> float:
    """Calculate the routing cost (weight) for a given edge.

    Supports both distance-weighted (shortest-path) and travel-time-weighted graphs.

    Args:
        edge_data: Dictionary of edge attributes.
        weight_type_or_lambda: Routing preference:
            - If "distance" or float/int 0.0: returns distance in meters.
            - If "time" or float/int > 0.0: returns travel time in seconds.
        model_type: Velocity model name ('glm', 'tobler', or 'naismith').
        ignore_downhill: If True, skips the downhill speed override.
        slope_multiplier: Elevation/slope multiplier to simulate pushing difficulty.

    Returns:
        The computed edge cost (weight).
    """
    distance = edge_data.get("distance", 0.0)

    # Determine routing weight mode
    is_distance = False
    if isinstance(weight_type_or_lambda, str):
        if weight_type_or_lambda.lower() == "distance":
            is_distance = True
    elif isinstance(weight_type_or_lambda, (int, float)):
        if weight_type_or_lambda == 0.0:
            is_distance = True

    if is_distance:
        return distance

    # Calculate travel time (seconds) using selected model speed (km/h)
    v_eff = get_velocity(edge_data, model_type, ignore_downhill, slope_multiplier)
    
    # Convert speed from km/h to m/s (1 km/h = 1/3.6 m/s)
    v_eff_mps = v_eff / 3.6
    
    # Travel time in seconds
    return distance / v_eff_mps
