"""Routing engine using NetworkX Dijkstra."""
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np
from scipy.spatial import KDTree

from .cost import calculate_cost


def build_kdtree(
    node_positions: Dict[int, Tuple[float, float]]
) -> Tuple[KDTree, List[int]]:
    """Build KDTree for fast nearest neighbor spatial search.

    The K-Dimensional Tree (KDTree) is a space-partitioning data structure 
    that allows for efficient O(log N) nearest neighbor queries, compared 
    to an O(N) naive linear search. This is essential for quickly snapping 
    arbitrary GPS coordinates to the nearest graph node.

    Args:
        node_positions: Mapping of node_id -> (latitude, longitude)

    Returns:
        Tuple containing:
        - The initialized scipy.spatial.KDTree instance
        - An ordered list of node IDs corresponding to the tree's internal array
    """
    nodes = list(node_positions.keys())
    # Convert node coordinates to a fast NumPy array for KDTree initialization
    positions = np.array([node_positions[n] for n in nodes])
    kdtree = KDTree(positions)
    return kdtree, nodes


def find_nearest_node(
    lat: float, lon: float, kdtree: KDTree, node_list: List[int],
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
    # Query the KDTree for the single nearest neighbor (k=1)
    # Returns (distance, index) where index points to the original array position
    _, idx = kdtree.query(point, k=1)
    return node_list[int(idx)]


def dijkstra_route(
    graph: nx.DiGraph, source: int, target: int, lambda_: float,
) -> Tuple[List[int], float, float]:
    """Find shortest path using Dijkstra's algorithm with an anisotropic cost function.

    This function utilizes NetworkX's Dijkstra implementation, but overrides 
    the standard static edge weight with a dynamic weighting function. The 
    dynamic cost computes a penalty based on uphill traversal severity (`lambda_`).

    Args:
        graph: NetworkX DiGraph object containing node/edge spatial data
        source: Starting node ID
        target: Destination node ID
        lambda_: The penalty factor applied to positive slopes (≥ 0)

    Returns:
        Tuple containing:
        - path: Ordered list of node IDs from source to target
        - total_distance: Sum of horizontal distances (in meters)
        - elevation_gain: Sum of all uphill climbs (in meters)
    
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
        return calculate_cost(d, lambda_)

    # Execute Dijkstra's shortest path algorithm
    path = nx.shortest_path(graph, source=source, target=target, weight=weight)

    total_distance = 0.0
    elevation_gain = 0.0

    # Re-iterate over the computed path to accumulate metric totals
    # This loop gathers final statistics to present to the user without
    # altering the routing logic itself.
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edge_data = graph[u][v]
        
        total_distance += edge_data.get("distance", 0)
        
        # Calculate elevation delta for this specific segment
        dh = edge_data.get("elevation_v", 0) - edge_data.get("elevation_u", 0)
        
        # Accumulate only positive elevation changes (uphill climbs)
        if dh > 0:
            elevation_gain += dh

    return path, total_distance, elevation_gain
