import sys
sys.path.append("/home/diaz/Documents/golekbengkel-backend-1")
import rasterio
import numpy as np
from config import DEMNAS_TIF, GRAPH_PATH
from core.graph_loader import get_graph

def check_bounds():
    dataset = rasterio.open(DEMNAS_TIF)
    print(f"DEMNAS Bounds: {dataset.bounds}")
    
    graph = get_graph(GRAPH_PATH)
    lats = [data['lat'] for _, data in graph.nodes(data=True)]
    lons = [data['lon'] for _, data in graph.nodes(data=True)]
    
    print(f"Graph Bounds: lons [{min(lons)}, {max(lons)}], lats [{min(lats)}, {max(lats)}]")
    
    # Let's see where the valid ones are
    valid_lats = []
    valid_lons = []
    for _, data in graph.nodes(data=True):
        col, row = ~dataset.transform * (data['lon'], data['lat'])
        val = dataset.read(1)[int(row), int(col)]
        if not np.isnan(val):
            valid_lats.append(data['lat'])
            valid_lons.append(data['lon'])
            
    if valid_lats:
        print(f"Valid Nodes Bounds: lons [{min(valid_lons)}, {max(valid_lons)}], lats [{min(valid_lats)}, {max(valid_lats)}]")

if __name__ == "__main__":
    check_bounds()
