"""Elevation sampling from DEMNAS raster.

DEMNAS (DEM Nasional) is a high-resolution elevation model from BIG (Badan
Informasi Geospasial) with ~0.27 arc-second (~8 meter) spatial resolution.
Data is in GeoTIFF format with EGM2008 vertical datum.
"""
import math
from typing import Dict, List, Optional, Tuple

import numpy as np
import rasterio


def load_demnas(tif_path: str) -> Tuple[np.ndarray, object, object]:
    """Load DEMNAS raster and return data needed for elevation sampling.

    Args:
        tif_path: Path to DEMNAS .tif file

    Returns:
        Tuple of (raster_data, transform, crs)
    """
    with rasterio.open(tif_path) as dataset:
        raster_data = dataset.read(1)  # band 1
        transform = dataset.transform
        crs = dataset.crs
    return raster_data, transform, crs


def geo_to_pixel(transform, lon: float, lat: float) -> Tuple[int, int]:
    """Convert geographic coordinates to pixel coordinates.

    CRITICAL: Note the order - col (x/lon), row (y/lat) for rasterio.

    Args:
        transform: Rasterio transform
        lon: Longitude
        lat: Latitude

    Returns:
        Tuple of (col, row) pixel coordinates
    """
    # Use inverse transform
    col, row = ~transform * (lon, lat)
    return int(col), int(row)


def sample_elevation(
    raster_data: np.ndarray,
    transform,
    lon: float,
    lat: float,
    method: str = "bilinear",
) -> Optional[float]:
    """Sample elevation at given coordinates using interpolation.

    Elevation models represent continuous terrain using discrete pixels. 
    Querying exact coordinates requires interpolation between these pixels.

    Args:
        raster_data: DEMNAS raster data (2D numpy array)
        transform: Rasterio affine transform mapping pixel space to geographic space
        lon: Target longitude
        lat: Target latitude
        method: Interpolation method:
                - 'nearest': Fast, snaps to the value of the closest pixel center.
                - 'bilinear': Weighted average of the 4 nearest pixels. Provides 
                  smoother transitions, which is critical for slope calculation
                  to avoid artificial "steps" at pixel boundaries.

    Returns:
        Elevation in meters, or None if the coordinate is outside the raster bounds.
    """
    col, row = geo_to_pixel(transform, lon, lat)

    # Check bounds
    height, width = raster_data.shape
    if col < 0 or col >= width or row < 0 or row >= height:
        return None

    if method == "nearest":
        val = float(raster_data[row, col])
        return 0.0 if math.isnan(val) else val
    else:
        # Bilinear interpolation
        row_f, col_f = math.floor(row), math.floor(col)
        row_c, col_c = math.ceil(row), math.ceil(col)

        # Clamp to bounds
        row_f = max(0, min(row_f, height - 1))
        row_c = max(0, min(row_c, height - 1))
        col_f = max(0, min(col_f, width - 1))
        col_c = max(0, min(col_c, width - 1))

        # Extract the 4 surrounding pixel values
        # If a pixel falls on a NoData value (NaN), it is cast to 0.0 to prevent 
        # NaN propagation throughout the downstream cost calculations.
        f00 = float(raster_data[row_f, col_f])
        f00 = 0.0 if math.isnan(f00) else f00
        
        f01 = float(raster_data[row_f, col_c])
        f01 = 0.0 if math.isnan(f01) else f01
        
        f10 = float(raster_data[row_c, col_f])
        f10 = 0.0 if math.isnan(f10) else f10
        
        f11 = float(raster_data[row_c, col_c])
        f11 = 0.0 if math.isnan(f11) else f11

        # Bilinear weights
        dy = row - row_f if row_f != row_c else 0
        dx = col - col_f if col_f != col_c else 0

        return float((1 - dy) * (1 - dx) * f00 + dy * (1 - dx) * f10 +
                     (1 - dy) * dx * f01 + dy * dx * f11)


def batch_sample_elevation(
    raster_data: np.ndarray,
    transform,
    coordinates: List[Tuple[float, float]],
    method: str = "nearest",
) -> Dict[int, Optional[float]]:
    """Sample elevation for multiple coordinates.

    Args:
        raster_data: DEMNAS raster data
        transform: Rasterio transform
        coordinates: List of (lon, lat) tuples
        method: 'nearest' or 'bilinear'

    Returns:
        Dict mapping index -> elevation
    """
    results = {}
    for i, (lon, lat) in enumerate(coordinates):
        elev = sample_elevation(raster_data, transform, lon, lat, method)
        results[i] = elev
    return results
