"""API routes with Swagger documentation."""
from flask import Blueprint, jsonify, request

from config import GRAPH_PATH
from core.graph_loader import get_graph, get_graph_info
from core.routing import dijkstra_route, find_nearest_node, build_kdtree
from .schemas import (
    RouteRequest,
)

api_bp = Blueprint("api", __name__)

# Memory caching (memoization) for spatial indexing structures.
# Rebuilding the KDTree and node lists on every request would be computationally
# expensive (O(N log N)). By caching these globally, we reduce subsequent
# nearest-node searches to O(log N) time complexity.
_kdtree_cache = None
_node_list_cache = None
_node_positions_cache = None


def get_cached_kdtree():
    """Get or build KDTree for nearest node search.
    
    Implements a lazy-loading Singleton/Memoization pattern to ensure the 
    KDTree is only built once during the application lifecycle.
    """
    global _kdtree_cache, _node_list_cache, _node_positions_cache

    if _kdtree_cache is None:
        graph = get_graph(GRAPH_PATH)
        # Extract all node coordinates to build the spatial index
        _node_positions_cache = {
            node: (data["lat"], data["lon"])
            for node, data in graph.nodes(data=True)
        }
        # Build the KDTree using scipy.spatial
        _kdtree_cache, _node_list_cache = build_kdtree(_node_positions_cache)

    return _kdtree_cache, _node_list_cache, _node_positions_cache


@api_bp.route("/route", methods=["POST"])
def route():
    """Find shortest path between two points.
    ---
    tags:
      - Routing
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - start
            - end
          properties:
            start:
              type: array
              items:
                type: number
              example: [-6.9, 112.0]
              description: "Start coordinates [lat, lon]"
            end:
              type: array
              items:
                type: number
              example: [-6.95, 112.05]
              description: "End coordinates [lat, lon]"
            lambda:
              type: number
              default: 0
              description: "Uphill penalty (0=normal, 3=semi-darurat, 5=darurat)"
    responses:
      200:
        description: Route found
        schema:
          type: object
          properties:
            path:
              type: array
              items:
                type: array
              description: List of [lat, lon] waypoints
            distance:
              type: number
              description: Total distance in meters
            elevation_gain:
              type: number
              description: Uphill elevation gain in meters
            mode:
              type: string
              description: Routing mode
            lambda_value:
              type: number
              description: Lambda value used
            node_count:
              type: integer
              description: Number of nodes in path
      400:
        description: Invalid input
      404:
        description: Route not found
    """
    data = request.get_json()

    try:
        req = RouteRequest(**data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    start_lat, start_lon = req.start
    end_lat, end_lon = req.end
    lambda_ = req.lambda_value or 0.0

    try:
        graph = get_graph(GRAPH_PATH)
        kdtree, node_list, node_positions = get_cached_kdtree()

        # 1. Map input geographic coordinates to the nearest nodes in the graph
        # This step is crucial because users rarely click exactly on a graph node.
        # KDTree spatial indexing allows this lookup to be highly efficient.
        src_node = find_nearest_node(start_lat, start_lon, kdtree, node_list)
        dst_node = find_nearest_node(end_lat, end_lon, kdtree, node_list)

        # 2. Compute the optimal route using Dijkstra's algorithm
        # The cost function dynamically adjusts edge weights based on the lambda penalty.
        path_indices, distance, elev_gain = dijkstra_route(
            graph, src_node, dst_node, lambda_
        )

        # Convert node indices back to geographic [lat, lon] coordinates 
        # required by the frontend mapping library (e.g., Leaflet/GeoJSON)
        path_coords = [
            [node_positions[n][0], node_positions[n][1]]
            for n in path_indices
        ]

        return jsonify({
            "path": path_coords,
            "distance": round(distance, 2),
            "elevation_gain": round(elev_gain, 2),
            "lambda_value": lambda_,
            "node_count": len(path_indices),
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Routing error: {str(e)}"}), 500


@api_bp.route("/nearest-node", methods=["GET"])
def nearest_node():
    """Find nearest graph node to coordinates.
    ---
    tags:
      - Utility
    parameters:
      - name: lat
        in: query
        type: number
        required: true
        description: Latitude
      - name: lon
        in: query
        type: number
        required: true
        description: Longitude
    responses:
      200:
        description: Nearest node found
        schema:
          type: object
          properties:
            node_id:
              type: integer
            lat:
              type: number
            lon:
              type: number
      400:
        description: Invalid coordinates
    """
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lon query params are required"}), 400

    try:
        kdtree, node_list, node_positions = get_cached_kdtree()
        node_id = find_nearest_node(lat, lon, kdtree, node_list)
        node_lat, node_lon = node_positions[node_id]

        return jsonify({
            "node_id": node_id,
            "lat": node_lat,
            "lon": node_lon,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/graph-info", methods=["GET"])
def graph_info():
    """Get graph statistics.
    ---
    tags:
      - Utility
    responses:
      200:
        description: Graph info
        schema:
          type: object
          properties:
            node_count:
              type: integer
            edge_count:
              type: integer
            is_directed:
              type: boolean
    """
    graph = get_graph(GRAPH_PATH)
    info = get_graph_info(graph)
    return jsonify(info)


