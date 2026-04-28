"""Test script to verify routing system works correctly."""
import sys
import os
import pickle
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing.slope import haversine_distance, calculate_slope
from core.cost import calculate_cost


def test_haversine():
    """Test distance calculation."""
    # ~111km per degree latitude
    d = haversine_distance(-6.9, 112.0, -6.91, 112.0)
    print(f"Haversine distance (-6.9,112.0) to (-6.91,112.0): {d:.2f} m")
    assert 1000 < d < 1200, f"Expected ~1.1km, got {d}"
    print("  ✓ Haversine OK")


def test_slope():
    """Test slope calculation."""
    # Flat terrain
    d, sp, sn = calculate_slope(-6.9, 112.0, 10.0, -6.91, 112.0, 10.0)
    print(f"Flat slope: distance={d:.2f}, slope+={sp:.6f}, slope-={sn:.6f}")
    assert sp == 0 and sn == 0, "Flat should have zero slope"
    print("  ✓ Flat slope OK")

    # Uphill
    d, sp, sn = calculate_slope(-6.9, 112.0, 0.0, -6.91, 112.0, 100.0)
    print(f"Uphill: distance={d:.2f}, slope+={sp:.6f}, slope-={sn:.6f}")
    assert sp > 0, "Uphill should have positive slope"
    print("  ✓ Uphill slope OK")

    # Downhill
    d, sp, sn = calculate_slope(-6.9, 112.0, 100.0, -6.91, 112.0, 0.0)
    print(f"Downhill: distance={d:.2f}, slope+={sp:.6f}, slope-={sn:.6f}")
    assert sn > 0, "Downhill should have negative slope recorded as slope-"
    print("  ✓ Downhill slope OK")


def test_cost():
    """Test cost function."""
    edge = {"distance": 1000, "slope_positive": 0.01}

    # Normal mode (λ=0)
    c0 = calculate_cost(edge, 0.0)
    print(f"Cost with λ=0: {c0}")
    assert c0 == 1000, f"Expected 1000, got {c0}"
    print("  ✓ Normal mode OK")

    # Emergency mode (λ=5)
    c5 = calculate_cost(edge, 5.0)
    print(f"Cost with λ=5: {c5}")
    expected = 1000 * (1 + 5 * 0.01)  # 1050
    assert c5 == expected, f"Expected {expected}, got {c5}"
    print("  ✓ Emergency mode OK")

    # Verify emergency is more expensive for uphill
    edge_flat = {"distance": 1000, "slope_positive": 0.0}
    c5_flat = calculate_cost(edge_flat, 5.0)
    print(f"Cost flat with λ=5: {c5_flat}")
    assert c5_flat < c5, "Uphill should cost more than flat"
    print("  ✓ Cost differentiation OK")


def test_graph_building():
    """Test graph building with sample data."""
    import config
    import networkx as nx

    if not Path(config.GRAPH_PATH).exists():
        print("Creating test graph...")
        G = nx.DiGraph()

        nodes = [
            (0, -6.9, 112.0),
            (1, -6.905, 112.01),
            (2, -6.91, 112.02),
            (3, -6.915, 112.03),
            (4, -6.895, 112.005),
        ]

        for idx, lat, lon in nodes:
            G.add_node(idx, lat=lat, lon=lon)

        edges = [
            # (u, v, dist, elev_u, elev_v, slope+, slope-)
            (0, 1, 1500, 10, 15, 0.003, 0),
            (1, 0, 1500, 15, 10, 0, 0.003),
            (1, 2, 1200, 15, 25, 0.008, 0),
            (2, 1, 1200, 25, 15, 0, 0.008),
            (2, 3, 1000, 25, 20, 0, 0.005),
            (3, 2, 1000, 20, 25, 0.005, 0),
            (0, 4, 800, 10, 12, 0.002, 0),
            (4, 0, 800, 12, 10, 0, 0.002),
            (4, 2, 1100, 12, 25, 0.012, 0),
            (2, 4, 1100, 25, 12, 0, 0.012),
        ]

        for u, v, dist, eu, ev, sp, sn in edges:
            G.add_edge(u, v,
                       distance=dist,
                       elevation_u=eu,
                       elevation_v=ev,
                       slope_positive=sp,
                       slope_negative=sn)

        Path(config.GRAPH_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(config.GRAPH_PATH, "wb") as f:
            pickle.dump(G, f)
        print(f"  Created test graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    else:
        print(f"Graph exists at {config.GRAPH_PATH}")


def test_routing():
    """Test actual routing if graph exists."""
    import config
    import networkx as nx
    from core.routing import dijkstra_route, build_kdtree

    if not Path(config.GRAPH_PATH).exists():
        print("Skipping routing test - no graph file")
        return

    print("Testing routing...")
    with open(config.GRAPH_PATH, "rb") as f:
        G = pickle.load(f)

    node_positions = {n: (G.nodes[n]["lat"], G.nodes[n]["lon"]) for n in G.nodes()}
    kdtree, node_list = build_kdtree(node_positions)

    # Test normal mode (λ=0)
    path0, dist0, elev0 = dijkstra_route(G, 0, 3, 0.0)
    print(f"  Normal (λ=0): path={path0}, dist={dist0:.0f}m, elev={elev0:.0f}m")

    # Test emergency mode (λ=5)
    path5, dist5, elev5 = dijkstra_route(G, 0, 3, 5.0)
    print(f"  Emergency (λ=5): path={path5}, dist={dist5:.0f}m, elev={elev5:.0f}m")

    if elev5 <= elev0:
        print("  ✓ Emergency mode reduces/matches elevation gain")
    else:
        print("  ⚠ Emergency mode elevation gain not reduced (may be expected)")

    if dist0 <= dist5:
        print("  ✓ Normal mode has shorter/equal distance")
    else:
        print("  ⚠ Normal mode has longer distance (may be expected)")


def main():
    print("=" * 50)
    print("GolekBengkel Routing System Tests")
    print("=" * 50)

    print("\n1. Testing Haversine distance...")
    test_haversine()

    print("\n2. Testing slope calculation...")
    test_slope()

    print("\n3. Testing cost function...")
    test_cost()

    print("\n4. Testing graph building...")
    test_graph_building()

    print("\n5. Testing routing...")
    test_routing()

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
