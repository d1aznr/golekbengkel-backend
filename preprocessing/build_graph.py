"""Build routing graph from GeoJSON road networks and DEMNAS elevation rasters.

This script acts as the primary data ingestion pipeline, creating a directed 
weighted graph (DiGraph) from:
1. GeoJSON road network data (e.g., exported from OpenStreetMap via Overpass Turbo).
2. DEMNAS (DEM Nasional) elevation raster (.tif).

Each node represents an intersection or inflection point with geographic coordinates (lat/lon). 
Each directed edge represents a road segment containing the following attributes:
- `distance`: Horizontal distance in meters (computed via Haversine formula).
- `elevation_u`, `elevation_v`: Absolute elevation at the start and end nodes.
- `slope_positive`: max(0, slope) - Used to compute the uphill travel penalty.
- `slope_negative`: max(0, -slope) - Represents downhill slope.

Crucially, the graph is *directed* because terrain slope creates asymmetric traversal costs:
traveling uphill from point A to B incurs a significantly higher energetic or time cost 
than traveling downhill from B to A.
"""
import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString

from .elevation import load_demnas, batch_sample_elevation
from .slope import calculate_slope


def load_geojson(geojson_path: str) -> gpd.GeoDataFrame:
    """Load GeoJSON road data.

    Filters out non-LineString geometries (e.g. Polygon for pedestrian areas).

    Args:
        geojson_path: Path to GeoJSON file

    Returns:
        GeoDataFrame with road segments
    """
    gdf = gpd.read_file(geojson_path)
    # Only keep LineString geometries (roads), filter out Polygons etc.
    gdf = gdf[gdf.geometry.type == "LineString"]
    return gdf


def extract_nodes_and_edges(
    gdf: gpd.GeoDataFrame,
) -> Tuple[List[Tuple[float, float]], List[Tuple[int, int]]]:
    """Extract unique nodes and edges from road LineStrings.

    Args:
        gdf: GeoDataFrame with road geometries

    Returns:
        Tuple of (list of (lat, lon) nodes, list of (u_idx, v_idx) edges)
    """
    # 1. Identify unique nodes
    # Collect all unique coordinates to serve as graph nodes
    coord_to_idx: Dict[Tuple[float, float], int] = {}
    nodes: List[Tuple[float, float]] = []

    for geom in gdf.geometry:
        if not isinstance(geom, LineString):
            continue

        coords = list(geom.coords)
        for lon, lat in coords:  # Note: GeoJSON natively uses (lon, lat) ordering
            # Rounding to 7 decimal places (~1.1cm precision) mitigates floating-point 
            # inconsistencies that can cause duplicate nodes for the same intersection.
            key = (round(lat, 7), round(lon, 7))
            if key not in coord_to_idx:
                coord_to_idx[key] = len(nodes)
                nodes.append(key)

    # 2. Construct edges
    # Build bidirectional edges between consecutive nodes in each LineString.
    edges: List[Tuple[int, int]] = []
    for geom in gdf.geometry:
        if not isinstance(geom, LineString):
            continue

        coords = list(geom.coords)
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]

            key1 = (round(lat1, 7), round(lon1, 7))
            key2 = (round(lat2, 7), round(lon2, 7))

            u = coord_to_idx[key1]
            v = coord_to_idx[key2]

            # Add both directions explicitly. Although physical roads may be 
            # bidirectional, the directed graph is required to model the 
            # asymmetric slope penalty (uphill vs. downhill).
            edges.append((u, v))
            edges.append((v, u))

    return nodes, edges


def build_graph(
    nodes: List[Tuple[float, float]],
    edges: List[Tuple[int, int]],
    raster_data,
    transform,
) -> nx.DiGraph:
    """Build weighted directed graph with elevation and slope attributes.

    Args:
        nodes: List of (lat, lon) coordinates
        edges: List of (u_idx, v_idx) node index pairs
        raster_data: DEMNAS raster data
        transform: Rasterio transform

    Returns:
        NetworkX DiGraph with edge attributes
    """
    G = nx.DiGraph()

    # Add nodes with lat/lon attributes
    for i, (lat, lon) in enumerate(nodes):
        G.add_node(i, lat=lat, lon=lon)

    # Sample elevations for all nodes
    # GeoJSON coords are (lon, lat) → convert for rasterio sampling
    coords_for_sampling = [(lon, lat) for lat, lon in nodes]
    elevations = batch_sample_elevation(raster_data, transform, coords_for_sampling)

    # Add directed edges with distance, elevation, and slope attributes
    for u, v in edges:
        lat_u, lon_u = nodes[u]
        lat_v, lon_v = nodes[v]

        elev_u = elevations.get(u, 0.0)
        if elev_u is None:
            elev_u = 0.0
            
        elev_v = elevations.get(v, 0.0)
        if elev_v is None:
            elev_v = 0.0

        distance, slope_positive, slope_negative = calculate_slope(
            lat_u, lon_u, elev_u,
            lat_v, lon_v, elev_v,
        )

        G.add_edge(u, v,
                   distance=distance,
                   elevation_u=elev_u,
                   elevation_v=elev_v,
                   slope_positive=slope_positive,
                   slope_negative=slope_negative)

    return G


def build_and_save_graph(
    geojson_path: str,
    demnas_path: str,
    output_path: str,
) -> nx.DiGraph:
    """Build complete routing graph from source data and save to disk.

    Pipeline:
    1. Load GeoJSON road network
    2. Load DEMNAS DEM raster
    3. Extract nodes and edges from LineStrings
    4. Sample elevation for each node
    5. Compute slope and distance for each edge
    6. Save as pickle (.pkl)

    Args:
        geojson_path: Path to roads GeoJSON
        demnas_path: Path to DEMNAS .tif
        output_path: Path to save .pkl graph

    Returns:
        Built NetworkX DiGraph
    """
    # Load data
    print(f"Loading GeoJSON from {geojson_path}...")
    gdf = load_geojson(geojson_path)
    print(f"  Loaded {len(gdf)} road segments")

    print(f"Loading DEMNAS from {demnas_path}...")
    raster_data, transform, crs = load_demnas(demnas_path)
    print(f"  Raster shape: {raster_data.shape}")

    # Extract nodes and edges
    print("Extracting nodes and edges...")
    nodes, edges = extract_nodes_and_edges(gdf)
    print(f"  Found {len(nodes)} nodes, {len(edges)} edges")

    # Build graph
    print("Building graph with elevation data...")
    G = build_graph(nodes, edges, raster_data, transform)
    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Save
    print(f"Saving graph to {output_path}...")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(G, f)
    print("Done!")

    return G


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

    build_and_save_graph(
        geojson_path=config.JALAN_GEOJSON,
        demnas_path=config.DEMNAS_TIF,
        output_path=config.GRAPH_PATH,
    )
