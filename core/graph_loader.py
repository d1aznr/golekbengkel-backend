"""Graph loader for precomputed NetworkX graphs.

Provides caching to avoid reloading the graph from disk on every request.
The graph is a directed weighted graph (DiGraph) stored as a pickle file.
"""
import pickle
from pathlib import Path
from typing import Optional

import networkx as nx

_graph: Optional[nx.DiGraph] = None


def load_graph(graph_path: str) -> nx.DiGraph:
    """Load precomputed graph from a serialized pickle file.

    Deserializes the NetworkX graph built during the preprocessing phase. 
    Pickle is used for its fast read times of complex Python objects, which 
    is critical for minimizing the API's initialization overhead.

    Args:
        graph_path: Absolute or relative path to the .pkl file.

    Returns:
        The fully hydrated NetworkX DiGraph object complete with edge attributes.

    Raises:
        FileNotFoundError: If the specified graph file is missing.
        TypeError: If the loaded object is not the expected DiGraph type.
    """
    path = Path(graph_path)

    if not path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    with open(path, "rb") as f:
        graph = pickle.load(f)

    if not isinstance(graph, nx.DiGraph):
        raise TypeError(f"Expected DiGraph, got {type(graph)}")

    return graph


def get_graph(graph_path: str) -> nx.DiGraph:
    """Retrieve the cached graph, loading it from disk only if necessary.

    Implements a Singleton pattern to ensure the memory-intensive graph 
    is loaded precisely once per application lifecycle, drastically reducing 
    subsequent request latencies.

    Args:
        graph_path: Path to the .pkl file.

    Returns:
        The cached NetworkX DiGraph instance.
    """
    global _graph

    if _graph is None:
        _graph = load_graph(graph_path)

    return _graph


def reload_graph(graph_path: str) -> nx.DiGraph:
    """Force reload graph from disk (invalidates cache).

    Args:
        graph_path: Path to .pkl file

    Returns:
        NetworkX DiGraph
    """
    global _graph
    _graph = load_graph(graph_path)
    return _graph


def get_graph_info(graph: nx.DiGraph) -> dict:
    """Get summary info about the graph.

    Args:
        graph: NetworkX DiGraph

    Returns:
        Dict with node_count, edge_count, is_directed
    """
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "is_directed": graph.is_directed(),
    }
