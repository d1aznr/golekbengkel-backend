"""Slope calculation utilities for edges.

Slope is computed as the ratio of elevation change to horizontal distance:
    s(u,v) = (h(v) - h(u)) / d(u,v)

Only positive slope (uphill) is used as a penalty in the cost function,
since uphill travel requires significantly more effort than downhill.
"""
import math
from typing import Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points on a sphere.

    The Haversine formula determines the shortest surface distance between two 
    points on a sphere given their longitudes and latitudes. It remains well-conditioned 
    for small distances (unlike the spherical law of cosines), making it ideal 
    for calculating edge lengths between adjacent graph nodes.

    Args:
        lat1, lon1: First point coordinates (in decimal degrees)
        lat2, lon2: Second point coordinates (in decimal degrees)

    Returns:
        Horizontal distance in meters
    """
    R = 6371000  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_slope(
    lat1: float, lon1: float, elev1: float,
    lat2: float, lon2: float, elev2: float,
) -> Tuple[float, float, float]:
    """Calculate slope parameters for an edge.

    Args:
        lat1, lon1, elev1: Start point (lat, lon, elevation in meters)
        lat2, lon2, elev2: End point (lat, lon, elevation in meters)

    Returns:
        Tuple of (distance, slope_positive, slope_negative)
        - distance: horizontal distance in meters
        - slope_positive: max(0, slope) for uphill penalty
        - slope_negative: max(0, -slope) for downhill
    """
    distance = haversine_distance(lat1, lon1, lat2, lon2)

    # Ensure we don't divide by zero for co-located nodes
    if distance == 0:
        return 0.0, 0.0, 0.0

    # Calculate slope as a ratio: Δh / d
    # e.g., 0.1 means a 10% gradient (10m rise over 100m run)
    delta_elev = elev2 - elev1
    slope = delta_elev / distance

    # Decompose the gradient into purely positive (uphill) and negative (downhill) components.
    # This decomposition allows the routing engine to apply an anisotropic penalty:
    # penalizing uphill traversal heavily, while treating downhill as neutral or low-cost.
    slope_positive = max(0.0, slope)
    slope_negative = max(0.0, -slope)

    return distance, slope_positive, slope_negative
