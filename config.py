"""Application configuration and environment constants.

This module centralizes all configuration parameters, file paths, and 
hyperparameters (like default lambda penalties) used across the routing engine.
Keeping these in a single file ensures maintainability and consistency.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data paths
DATA_DIR = os.path.join(BASE_DIR, "data")
GRAPH_PATH = os.path.join(DATA_DIR, "graph.pkl")
JALAN_GEOJSON = os.path.join(DATA_DIR, "export.geojson")
DEMNAS_TIF = os.path.join(DATA_DIR, "DEMNAS_merged.tif")



# Coordinate search radius (in meters)
NEAREST_NODE_RADIUS = 1000  # meters

# API
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True
