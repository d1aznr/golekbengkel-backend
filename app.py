"""Flask application entry point with Swagger/OpenAPI documentation.

GolekBengkel - Graph-based routing API with a slope-aware cost function
for finding optimal routes to the nearest bengkel (workshop) in
hilly terrain (Kabupaten Tuban). This module initializes the web server,
registers API routes, and handles the initial loading of the precomputed
spatial graph into memory.
"""
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger

from config import HOST, PORT, DEBUG, GRAPH_PATH
from api.routes import api_bp
from core.graph_loader import get_graph, get_graph_info

# Configure standard logging for academic-level traceability
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_app(graph_path: str = GRAPH_PATH) -> Flask:
    """Create and configure Flask application.

    Args:
        graph_path: Path to precomputed graph .pkl file

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Enable Cross-Origin Resource Sharing (CORS) to allow frontend applications
    # (e.g., React/Vue running on a different port) to consume this API securely.
    CORS(app)

    # Swagger configuration for automated, interactive API documentation.
    # This aligns with professional API development standards, ensuring the
    # API endpoints are easily discoverable and testable.
    app.config["SWAGGER"] = {
        "title": "GolekBengkel Routing API",
        "description": (
            "Graph-based routing engine with an anisotropic, slope-aware cost function.\n\n"
            "## Cost Function\n"
            "The cost between node u and v is computed as:\n"
            "`Cost(u,v) = d(u,v) × (1 + λ × s⁺)`\n\n"
            "Where:\n"
            "- `d(u,v)` is the Haversine distance in meters.\n"
            "- `λ` is the user-defined penalty parameter for uphill traversal.\n"
            "- `s⁺` is the positive slope component (max(0, slope)).\n\n"
            "### Lambda Slider:\n"
            "The lambda value is set dynamically via a frontend slider, "
            "allowing fine-grained control over how aggressively the routing engine avoids hills.\n\n"
            "This system uses a directed weighted graph built from DEMNAS elevation data "
            "and OpenStreetMap road networks, utilizing Dijkstra's algorithm for optimal pathfinding."
        ),
        "version": "1.0.0",
        "uiversion": 3,
    }

    Swagger(app)

    # Register blueprints to modularize routing logic
    app.register_blueprint(api_bp, url_prefix="/api")

    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint.
        ---
        tags:
          - System
        responses:
          200:
            description: Service is healthy
        """
        return jsonify({"status": "ok"})

    # Root endpoint with API info
    @app.route("/", methods=["GET"])
    def index():
        """API root with endpoint listing.
        ---
        tags:
          - System
        responses:
          200:
            description: API information
        """
        return jsonify({
            "name": "GolekBengkel Routing API",
            "version": "1.0.0",
            "description": "Slope-aware routing for Kabupaten Tuban",
            "docs": "/apidocs",
            "endpoints": {
                "route": "POST /api/route",
                "nearest_node": "GET /api/nearest-node",
                "graph_info": "GET /api/graph-info",
            },
        })

    # Try to load the precomputed routing graph into memory upon application startup.
    # This prevents cold-start delays on the first API request.
    try:
        graph = get_graph(graph_path)
        info = get_graph_info(graph)
        logger.info(f"Graph loaded successfully: {info['node_count']} nodes, {info['edge_count']} edges")
    except FileNotFoundError:
        logger.warning(f"Graph file not found at {graph_path}. The API will not be able to route requests.")
        logger.warning("Please run the preprocessing script first: python -m preprocessing.build_graph")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
