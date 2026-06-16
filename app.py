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
            "Graph-based routing engine with an anisotropic, slope-aware travel time cost function "
            "for finding optimal routes to the nearest workshop in hilly terrains (Kabupaten Tuban).\n\n"
            "### 1. Travel Time Weight Function\n"
            "The routing engine calculates travel time as the graph edge cost:\n\n"
            "&nbsp;&nbsp;&nbsp;&nbsp;**T = d / (v_eff / 3.6)**\n\n"
            "Where:\n"
            "- **T**: Travel time in seconds\n"
            "- **d**: Horizontal distance in meters\n"
            "- **v_eff**: Effective walking speed in km/h (minimum clamped at 0.1 km/h)\n"
            "- **3.6**: Unit conversion factor to convert speed from km/h to m/s (1 km/h = 1/3.6 m/s)\n\n"
            "--- \n"
            "### 2. Velocity Estimation Models (v_eff)\n"
            "You can select from three speed models using the `model` parameter:\n\n"
            "#### A. Generalized Linear Model (GLM - Wood et al., 2023)\n"
            "Empirical model incorporating both local walking slope and surrounding terrain slope:\n"
            "- **Downhill** (walking slope θ < 0°): `v_eff = 5.0 km/h`\n"
            "- **Flat / Uphill** (walking slope θ ≥ 0°):\n"
            "```\n"
            "v_eff = exp(a + b·φ_eff + c·θ_eff + d·θ_eff²) km/h\n"
            "```\n"
            "*(Where a, b, c, d are coefficients based on road type: paved, unpaved, or off-road)*\n\n"
            "#### B. Tobler's Hiking Function\n"
            "Classic exponential speed model based on the hiking gradient:\n"
            "```\n"
            "v_eff = 6 · exp(-3.5 · |s_eff + 0.05|) km/h\n"
            "```\n\n"
            "#### C. Naismith's Rule\n"
            "Linear rule of thumb adding 10 minutes of travel time per 100 meters of ascent:\n"
            "```\n"
            "v_eff = 5 · d / (d + 8.3333 · max(0, Δh_eff)) km/h\n"
            "```\n\n"
            "--- \n"
            "### 3. Slope Scaling & Downhill Override\n"
            "- **Slope Multiplier (k)**: Simulates physical load difficulty (e.g. pushing a motorcycle). "
            "It scales the inputs before speed calculation:\n"
            "  - Effective Walking Slope: θ_eff = arctan(k · tan(θ))\n"
            "  - Effective Gradient: s_eff = k · s\n"
            "  - Effective Ascent: Δh_eff = k · Δh\n"
            "- **Downhill Override**: Downhill segments default to a constant `5.0 km/h` for motorable/gravity assistance. "
            "Set `ignore_downhill: true` to run the model's native equation on downhills."
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
