#!/usr/bin/env bash

# Setup script for golekbengkel backend
# Creates virtual environment and installs dependencies

set -e

echo "=========================================="
echo "GolekBengkel Backend Setup"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Detected Python: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "  Venv already exists, skipping..."
else
    python3 -m venv .venv
    echo "  Created .venv/"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Setup data directory
echo ""
echo "Setting up data directory..."
mkdir -p data

# Check for data files
if [ ! -f "data/export.geojson" ]; then
    echo "WARNING: data/export.geojson not found"
    echo "TIPS: You can get it from Overpass API: https://overpass-turbo.eu/"
    exit 1
fi

if [ ! -f "data/DEMNAS_merged.tif" ]; then
    echo "WARNING: data/DEMNAS_merged.tif not found"
    echo "TIPS: You can get it from https://tanahair.indonesia.go.id/portal-web/unduh/demnas (login first)"
    exit 1
fi

# Build graph or create test graph
if [ ! -f "data/graph.pkl" ]; then
    echo ""
    if [ -f "data/export.geojson" ] && [ -f "data/DEMNAS_merged.tif" ]; then
        echo "Building graph from real data..."
        python -m preprocessing.build_graph
    else
        echo "Creating minimal test graph..."
        python test_routing.py
    fi
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To start the API server:"
echo "  ./run.sh"
echo ""
echo "Swagger docs: http://localhost:5000/apidocs"
echo "=========================================="
