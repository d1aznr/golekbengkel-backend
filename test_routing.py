"""Test script to verify routing system works correctly."""
import sys
import os
import pickle
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocessing.slope import haversine_distance, calculate_slope
from core.cost import calculate_cost, get_velocity

TEST_GRAPH_PATH = "data/test_graph.pkl"



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
    """Test cost function using different speed models and options."""
    # 1. Paved road uphill
    edge_uphill = {
        "distance": 1000,
        "walking_slope_deg": 5.0,
        "hill_slope_deg": 2.0,
        "road_type": "paved_road",
        "elevation_u": 10.0,
        "elevation_v": 60.0
    }

    # Distance mode
    c_dist = calculate_cost(edge_uphill, "distance")
    print(f"Cost distance mode: {c_dist}")
    assert c_dist == 1000, f"Expected 1000, got {c_dist}"
    print("  ✓ Distance mode OK")

    # Time mode (using GLM, slope_multiplier=1.0 for hiker baseline)
    c_time = calculate_cost(edge_uphill, "time", model_type="glm", slope_multiplier=1.0)
    print(f"Cost time mode (GLM, multiplier=1.0): {c_time:.2f} s")
    assert 800 < c_time < 850, f"Expected ~818s, got {c_time}"
    print("  ✓ GLM time mode (multiplier=1.0) OK")

    # Downhill GLM (default downhill = 5km/h, multiplier=1.0)
    edge_downhill = {
        "distance": 1000,
        "walking_slope_deg": -2.0,
        "hill_slope_deg": 2.0,
        "road_type": "paved_road",
        "elevation_u": 60.0,
        "elevation_v": 10.0
    }
    c_downhill = calculate_cost(edge_downhill, "time", model_type="glm", ignore_downhill=False, slope_multiplier=1.0)
    print(f"Cost downhill mode (GLM, override, multiplier=1.0): {c_downhill:.2f} s")
    assert abs(c_downhill - 720.0) < 0.1, f"Expected 720s, got {c_downhill}"
    print("  ✓ Downhill constant speed OK")

    # Downhill GLM with ignore_downhill=True, multiplier=1.0
    c_downhill_ignored = calculate_cost(edge_downhill, "time", model_type="glm", ignore_downhill=True, slope_multiplier=1.0)
    print(f"Cost downhill mode (GLM, ignored override, multiplier=1.0): {c_downhill_ignored:.2f} s")
    assert 740 < c_downhill_ignored < 745, f"Expected ~743s, got {c_downhill_ignored}"
    print("  ✓ Downhill ignored override (GLM equation) OK")

    # Tobler model (uphill, multiplier=1.0)
    # s = 50 / 1000 = 0.05. v = 6 * exp(-3.5 * 0.1) = 6 * exp(-0.35) = 4.229 km/h
    # v_mps = 4.229 / 3.6 = 1.1747 m/s. time = 1000 / 1.1747 = 851.27 s
    c_tobler_uphill = calculate_cost(edge_uphill, "time", model_type="tobler", slope_multiplier=1.0)
    print(f"Cost uphill (Tobler, multiplier=1.0): {c_tobler_uphill:.2f} s")
    assert 845 < c_tobler_uphill < 855, f"Expected ~851s, got {c_tobler_uphill}"
    print("  ✓ Tobler uphill OK")

    # Tobler model (downhill ignored override, multiplier=1.0)
    # s = -50 / 1000 = -0.05. v = 6 * exp(-3.5 * 0.0) = 6.0 km/h
    # v_mps = 6.0 / 3.6 = 1.6667 m/s. time = 1000 / 1.6667 = 600 s
    c_tobler_downhill = calculate_cost(edge_downhill, "time", model_type="tobler", ignore_downhill=True, slope_multiplier=1.0)
    print(f"Cost downhill (Tobler, ignored override, multiplier=1.0): {c_tobler_downhill:.2f} s")
    assert abs(c_tobler_downhill - 600.0) < 0.1, f"Expected 600s, got {c_tobler_downhill}"
    print("  ✓ Tobler downhill ignored override OK")

    # Naismith model (uphill, multiplier=1.0)
    # distance = 1000m, delta_h = 50m. v = 5 * 1000 / (1000 + 8.3333 * 50) = 3.529 km/h
    # v_mps = 3.529 / 3.6 = 0.9804 m/s. time = 1000 / 0.9804 = 1020 s
    c_naismith_uphill = calculate_cost(edge_uphill, "time", model_type="naismith", slope_multiplier=1.0)
    print(f"Cost uphill (Naismith, multiplier=1.0): {c_naismith_uphill:.2f} s")
    assert abs(c_naismith_uphill - 1020.0) < 0.1, f"Expected 1020s, got {c_naismith_uphill}"
    print("  ✓ Naismith uphill OK")

    # 3. Test Pushing Motorcycle (slope_multiplier = 3.0)
    # GLM: theta_eff = 14.707°, phi_eff = 5.978° -> time ~ 1353s
    c_time_scaled = calculate_cost(edge_uphill, "time", model_type="glm", slope_multiplier=3.0)
    print(f"Cost time mode (GLM, multiplier=3.0): {c_time_scaled:.2f} s")
    assert 1340 < c_time_scaled < 1370, f"Expected ~1353s, got {c_time_scaled}"

    # Tobler: s_eff = 3 * 0.05 = 0.15 -> time ~ 1208s
    c_tobler_scaled = calculate_cost(edge_uphill, "time", model_type="tobler", slope_multiplier=3.0)
    print(f"Cost uphill (Tobler, multiplier=3.0): {c_tobler_scaled:.2f} s")
    assert 1200 < c_tobler_scaled < 1220, f"Expected ~1208s, got {c_tobler_scaled}"

    # Naismith: delta_h_eff = 3 * 50 = 150m -> time = 1620s
    c_naismith_scaled = calculate_cost(edge_uphill, "time", model_type="naismith", slope_multiplier=3.0)
    print(f"Cost uphill (Naismith, multiplier=3.0): {c_naismith_scaled:.2f} s")
    assert abs(c_naismith_scaled - 1620.0) < 0.1, f"Expected 1620s, got {c_naismith_scaled}"
    print("  ✓ Slope scaling (multiplier=3.0) tests OK")


def test_graph_building():
    """Test graph building with sample data containing new attributes."""
    import config
    import networkx as nx

    # Recreate the test graph to ensure it contains the new attributes
    print("Creating test graph with GLM attributes...")
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
        # (u, v, dist, elev_u, elev_v, slope+, slope-, walking_slope_deg, hill_slope_deg, road_type)
        (0, 1, 1500, 10, 15, 0.003, 0, 0.19, 1.2, "paved_road"),
        (1, 0, 1500, 15, 10, 0, 0.003, -0.19, 1.2, "paved_road"),
        (1, 2, 1200, 15, 25, 0.008, 0, 0.48, 2.5, "paved_road"),
        (2, 1, 1200, 25, 15, 0, 0.008, -0.48, 2.5, "paved_road"),
        (2, 3, 1000, 25, 20, 0, 0.005, -0.29, 1.8, "unpaved_road"),
        (3, 2, 1000, 20, 25, 0.005, 0, 0.29, 1.8, "unpaved_road"),
        (0, 4, 800, 10, 12, 0.002, 0, 0.14, 0.8, "paved_road"),
        (4, 0, 800, 12, 10, 0, 0.002, -0.14, 0.8, "paved_road"),
        (4, 2, 1100, 12, 25, 0.012, 0, 0.68, 3.1, "unpaved_road"),
        (2, 4, 1100, 25, 12, 0, 0.012, -0.68, 3.1, "unpaved_road"),
    ]

    for u, v, dist, eu, ev, sp, sn, ws, hs, rt in edges:
        G.add_edge(u, v,
                   distance=dist,
                   elevation_u=eu,
                   elevation_v=ev,
                   slope_positive=sp,
                   slope_negative=sn,
                   walking_slope_deg=ws,
                   hill_slope_deg=hs,
                   road_type=rt)

    Path(TEST_GRAPH_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(TEST_GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)
    print(f"  Created test graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")


def test_routing():
    """Test actual routing using distance and time weight modes with different models."""
    import config
    import networkx as nx
    from core.routing import dijkstra_route, build_kdtree

    with open(TEST_GRAPH_PATH, "rb") as f:
        G = pickle.load(f)

    node_positions = {n: (G.nodes[n]["lat"], G.nodes[n]["lon"]) for n in G.nodes()}
    kdtree, node_list = build_kdtree(node_positions)

    # Test distance routing (mode = "distance")
    path_d, dist_d, elev_d, time_d, chars_d = dijkstra_route(G, 0, 3, "distance")
    print(f"  Distance Mode: path={path_d}, dist={dist_d:.0f}m, time={time_d:.0f}s, avg_slope={chars_d['average_slope_deg']}°")

    # Test GLM
    path_glm, dist_glm, elev_glm, time_glm, chars_glm = dijkstra_route(G, 0, 3, "time", model_type="glm")
    print(f"  GLM Mode: path={path_glm}, dist={dist_glm:.0f}m, time={time_glm:.0f}s, avg_slope={chars_glm['average_slope_deg']}°")

    # Test Tobler
    path_tob, dist_tob, elev_tob, time_tob, chars_tob = dijkstra_route(G, 0, 3, "time", model_type="tobler")
    print(f"  Tobler Mode: path={path_tob}, dist={dist_tob:.0f}m, time={time_tob:.0f}s, avg_slope={chars_tob['average_slope_deg']}°")

    # Test Naismith
    path_nai, dist_nai, elev_nai, time_nai, chars_nai = dijkstra_route(G, 0, 3, "time", model_type="naismith")
    print(f"  Naismith Mode: path={path_nai}, dist={dist_nai:.0f}m, time={time_nai:.0f}s, avg_slope={chars_nai['average_slope_deg']}°")

    # Test ignore_downhill
    path_ign, dist_ign, elev_ign, time_ign, chars_ign = dijkstra_route(G, 0, 3, "time", model_type="glm", ignore_downhill=True)
    print(f"  GLM (Ignore Downhill): path={path_ign}, dist={dist_ign:.0f}m, time={time_ign:.0f}s, avg_slope={chars_ign['average_slope_deg']}°")

    assert len(path_d) > 0, "Distance path should be non-empty"
    assert len(path_glm) > 0, "GLM path should be non-empty"
    assert len(path_tob) > 0, "Tobler path should be non-empty"
    assert len(path_nai) > 0, "Naismith path should be non-empty"
    print("  ✓ Routing execution and metrics extraction OK")


def main():
    print("=" * 50)
    print("GolekBengkel Routing System Tests (GLM Update)")
    print("=" * 50)

    print("\n1. Testing Haversine distance...")
    test_haversine()

    print("\n2. Testing slope calculation...")
    test_slope()

    print("\n3. Testing cost function (GLM)...")
    test_cost()

    print("\n4. Testing graph building (GLM)...")
    test_graph_building()

    print("\n5. Testing routing (GLM vs Distance)...")
    test_routing()

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
