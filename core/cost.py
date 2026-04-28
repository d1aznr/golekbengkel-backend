"""Dynamic cost function for routing.

Cost(u,v) = d(u,v) * (1 + λ * s⁺)

Where:
- d(u,v) = horizontal distance between nodes u and v
- λ (lambda) = slope penalty parameter (user-controllable)
- s⁺ = max(0, slope) = positive slope component (uphill only)

Behavior:
- λ = 0 → pure shortest path (ignores elevation)
- λ > 0 → penalizes uphill climbs proportionally

This is a linear anisotropic cost model commonly used in
least-cost path analysis on hilly terrain.
"""

from typing import Dict


def calculate_cost(edge_data: Dict, lambda_: float) -> float:
    """Calculate the anisotropic routing cost for an edge.

    This implements the core theoretical model of the application. The cost 
    is a linear combination of physical distance and a penalty applied to 
    uphill elevation changes. This creates an anisotropic graph where:
    Cost(A→B) != Cost(B→A) if the elevations of A and B differ.

    Args:
        edge_data: Dictionary containing 'distance' and 'slope_positive' metrics.
        lambda_: User-defined severity multiplier for uphill slopes. 
                 Higher values increasingly favor flatter, potentially longer routes.

    Returns:
        The computed edge cost (guaranteed to be ≥ 0 to satisfy Dijkstra's requirement).
    """
    distance = edge_data.get("distance", 0)
    slope_positive = edge_data.get("slope_positive", 0)

    # Base distance scaled by the slope penalty factor.
    # If lambda_ is 0, this degenerates to pure shortest-path routing.
    return distance * (1 + lambda_ * slope_positive)


