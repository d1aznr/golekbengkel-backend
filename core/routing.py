"""Routing engine using NetworkX Dijkstra and GLM speed weights."""

from typing import Dict, List, Tuple, Union
import networkx as nx
import numpy as np
from scipy.spatial import KDTree

from .cost import calculate_cost


def build_kdtree(
    node_positions: Dict[int, Tuple[float, float]]
) -> Tuple[KDTree, List[int]]:
    """Build KDTree for fast nearest neighbor spatial search.

    Args:
        node_positions: Mapping of node_id -> (latitude, longitude)

    Returns:
        Tuple containing:
        - The initialized scipy.spatial.KDTree instance
        - An ordered list of node IDs corresponding to the tree's internal array
    """
    nodes = list(node_positions.keys())
    positions = np.array([node_positions[n] for n in nodes])
    kdtree = KDTree(positions)
    return kdtree, nodes


def find_nearest_node(
    lat: float, lon: float, kdtree: KDTree, node_list: List[int]
) -> int:
    """Find nearest graph node to given coordinates using the spatial index.

    Args:
        lat: Latitude of the query point
        lon: Longitude of the query point
        kdtree: Pre-built spatial KDTree
        node_list: Ordered list of node IDs matching the KDTree structure

    Returns:
        ID of the nearest graph node
    """
    point = np.array([lat, lon])
    _, idx = kdtree.query(point, k=1)
    return node_list[int(idx)]


def dijkstra_route(
    graph: nx.DiGraph,
    source: int,
    target: int,
    weight_type_or_lambda: Union[str, float] = "time",
    model_type: str = "glm",
    ignore_downhill: bool = False,
    slope_multiplier: float = 3.0,
) -> Tuple[List[int], float, float, float, Dict]:
    """Find shortest path using Dijkstra's algorithm.

    Weights the graph by either horizontal distance or travel time based on the
    selected velocity model (GLM, Tobler, or Naismith).

    Args:
        graph: NetworkX DiGraph object containing node/edge spatial data
        source: Starting node ID
        target: Destination node ID
        weight_type_or_lambda: Routing weight preference (e.g. "time", "distance", or lambda)
        model_type: Velocity model name ('glm', 'tobler', or 'naismith')
        ignore_downhill: Whether to ignore the constant 5km/h downhill speed rule
        slope_multiplier: Elevation/slope multiplier to simulate pushing difficulty

    Returns:
        Tuple containing:
        - path: Ordered list of node IDs from source to target
        - total_distance: Sum of horizontal distances (in meters)
        - elevation_gain: Sum of all uphill climbs (in meters)
        - total_time: Total travel time (in seconds)
        - slope_characteristics: Dictionary of slope statistics (degrees, ratios)

    Raises:
        ValueError: If source or target nodes do not exist in the graph.
        nx.NetworkXNoPath: If no path exists between source and target.
    """
    if source not in graph:
        raise ValueError(f"Source node {source} not in the graph topology.")
    if target not in graph:
        raise ValueError(f"Target node {target} not in the graph topology.")

    # Define the dynamic weight function injected into NetworkX
    def weight(u: int, v: int, d: Dict) -> float:
        return calculate_cost(
            d,
            weight_type_or_lambda=weight_type_or_lambda,
            model_type=model_type,
            ignore_downhill=ignore_downhill,
            slope_multiplier=slope_multiplier,
        )

    # Execute Dijkstra's shortest path algorithm
    path = nx.shortest_path(graph, source=source, target=target, weight=weight)

    total_distance = 0.0
    elevation_gain = 0.0
    total_time = 0.0

    slopes = []
    uphill_meters = 0.0
    downhill_meters = 0.0
    flat_meters = 0.0

    # Accumulate metrics over the path segments
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = graph[u][v]

        dist = edge_data.get("distance", 0.0)
        total_distance += dist

        # Elevation delta
        dh = edge_data.get("elevation_v", 0.0) - edge_data.get("elevation_u", 0.0)
        if dh > 0:
            elevation_gain += dh

        # Estimated travel time (always in seconds, using the selected time weight)
        segment_time = calculate_cost(
            edge_data,
            weight_type_or_lambda="time",
            model_type=model_type,
            ignore_downhill=ignore_downhill,
            slope_multiplier=slope_multiplier,
        )
        total_time += segment_time

        # Walking slope in degrees
        walking_slope = edge_data.get("walking_slope_deg", 0.0)
        slopes.append(walking_slope)

        # Segment slope classification:
        # - Uphill: slope >= 1.0 degree
        # - Downhill: slope <= -1.0 degree
        # - Flat: slope between -1.0 and 1.0 degree
        if walking_slope >= 1.0:
            uphill_meters += dist
        elif walking_slope <= -1.0:
            downhill_meters += dist
        else:
            flat_meters += dist

    # Calculate aggregate slope characteristics
    avg_slope = float(np.mean(slopes)) if slopes else 0.0
    max_slope = float(np.max([abs(s) for s in slopes])) if slopes else 0.0

    slope_characteristics = {
        "average_slope_deg": round(avg_slope, 2),
        "max_slope_deg": round(max_slope, 2),
        "uphill_meters": round(uphill_meters, 2),
        "downhill_meters": round(downhill_meters, 2),
        "flat_meters": round(flat_meters, 2),
        "uphill_ratio": round(uphill_meters / total_distance, 4) if total_distance > 0 else 0.0,
        "downhill_ratio": round(downhill_meters / total_distance, 4) if total_distance > 0 else 0.0,
        "flat_ratio": round(flat_meters / total_distance, 4) if total_distance > 0 else 0.0,
    }

    return path, total_distance, elevation_gain, total_time, slope_characteristics
