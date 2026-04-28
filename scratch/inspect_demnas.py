import sys
sys.path.append("/home/diaz/Documents/golekbengkel-backend-1")
import rasterio
import numpy as np
from config import DEMNAS_TIF

def inspect_demnas():
    print(f"Loading DEMNAS from {DEMNAS_TIF}")
    with rasterio.open(DEMNAS_TIF) as dataset:
        raster_data = dataset.read(1)
        print(f"Raster shape: {raster_data.shape}")
        print(f"Nodata value: {dataset.nodata}")
        print(f"Min: {np.nanmin(raster_data)}, Max: {np.nanmax(raster_data)}")
        
        # Test a coordinate we know is in the graph
        # Node 0: (lat=-7.096523, lon=112.1744595)
        lon = 112.1744595
        lat = -7.096523
        col, row = ~dataset.transform * (lon, lat)
        col, row = int(col), int(row)
        print(f"Node 0 -> col: {col}, row: {row}")
        
        if 0 <= col < raster_data.shape[1] and 0 <= row < raster_data.shape[0]:
            val = raster_data[row, col]
            print(f"Value at pixel: {val}")
        else:
            print("Pixel is OUT OF BOUNDS!")

if __name__ == "__main__":
    inspect_demnas()
