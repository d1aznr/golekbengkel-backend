#!/usr/bin/env bash

# Run script for golekbengkel backend
# Starts the Flask application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found."
    echo "Please run setup.sh first to set up the environment."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check for graph file
if [ ! -f "data/graph.pkl" ]; then
    echo "WARNING: Graph file not found at data/graph.pkl"
    echo "You may need to build the graph first:"
    echo "  python -m preprocessing.build_graph"
    echo "  or use test graph: python test_routing.py"
fi

# Run the application
python app.py
