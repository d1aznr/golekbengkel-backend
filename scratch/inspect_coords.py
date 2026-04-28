import sys
sys.path.append("/home/diaz/Documents/golekbengkel-backend-1")
from config import GRAPH_PATH
from core.graph_loader import get_graph
import numpy as np

def inspect():
    graph = get_graph(GRAPH_PATH)
    lats = [data['lat'] for _, data in graph.nodes(data=True)]
    lons = [data['lon'] for _, data in graph.nodes(data=True)]
    
    print(f"Graph Bounds:")
    print(f"Lat: {np.min(lats):.4f} to {np.max(lats):.4f}")
    print(f"Lon: {np.min(lons):.4f} to {np.max(lons):.4f}")
    
    # Sample a few nodes with valid elevation vs NaN elevation
    import rasterio
    from config import DEMNAS_TIF
    dataset = rasterio.open(DEMNAS_TIF)
    raster_data = dataset.read(1)
    
    valid_samples = []
    nan_samples = []
    
    for i, (_, data) in enumerate(graph.nodes(data=True)):
        col, row = ~dataset.transform * (data['lon'], data['lat'])
        val = raster_data[int(row), int(col)]
        if np.isnan(val):
            if len(nan_samples) < 5:
                nan_samples.append((data['lat'], data['lon']))
        else:
            if len(valid_samples) < 5:
                valid_samples.append((data['lat'], data['lon'], val))
                
        if len(nan_samples) >= 5 and len(valid_samples) >= 5:
            break
            
    print("\nValid samples (lat, lon, elev):")
    for s in valid_samples:
        print(s)
        
    print("\nNaN samples (lat, lon):")
    for s in nan_samples:
        print(s)

if __name__ == "__main__":
    inspect()
