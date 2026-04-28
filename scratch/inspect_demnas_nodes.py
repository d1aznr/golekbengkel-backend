import sys
sys.path.append("/home/diaz/Documents/golekbengkel-backend-1")
import rasterio
import numpy as np
from config import DEMNAS_TIF, GRAPH_PATH
from core.graph_loader import get_graph

def inspect_demnas_nodes():
    print(f"Loading DEMNAS from {DEMNAS_TIF}")
    dataset = rasterio.open(DEMNAS_TIF)
    raster_data = dataset.read(1)
    
    print(f"Loading Graph from {GRAPH_PATH}")
    graph = get_graph(GRAPH_PATH)
    
    nan_count = 0
    valid_count = 0
    out_of_bounds = 0
    
    for idx, (node_id, data) in enumerate(graph.nodes(data=True)):
        lat = data['lat']
        lon = data['lon']
        col, row = ~dataset.transform * (lon, lat)
        col, row = int(col), int(row)
        
        if 0 <= col < raster_data.shape[1] and 0 <= row < raster_data.shape[0]:
            val = raster_data[row, col]
            if np.isnan(val):
                nan_count += 1
            else:
                valid_count += 1
        else:
            out_of_bounds += 1
            
    print(f"Total Nodes: {graph.number_of_nodes()}")
    print(f"Valid Elevation: {valid_count}")
    print(f"NaN Elevation: {nan_count}")
    print(f"Out of Bounds: {out_of_bounds}")

if __name__ == "__main__":
    inspect_demnas_nodes()
