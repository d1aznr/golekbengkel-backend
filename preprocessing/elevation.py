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


def calculate_terrain_slope(
    raster_data: np.ndarray,
    transform,
    lon: float,
    lat: float,
) -> float:
    """Calculate terrain slope (gradient of steepest descent) in degrees at a point.

    Uses Horn's method on a 3x3 neighborhood around the target coordinate.
    Converts geographic cell sizes to meters based on the latitude.

    Args:
        raster_data: DEMNAS raster data (2D numpy array)
        transform: Rasterio transform
        lon: Longitude
        lat: Latitude

    Returns:
        Terrain slope in degrees (always >= 0)
    """
    col, row = geo_to_pixel(transform, lon, lat)
    height, width = raster_data.shape

    # Clamp coordinates to bounds, leaving a 1-pixel border to allow 3x3 window
    r = max(1, min(row, height - 2))
    c = max(1, min(col, width - 2))

    # Read 3x3 neighborhood elevation values
    z11 = float(raster_data[r - 1, c - 1])
    z12 = float(raster_data[r - 1, c])
    z13 = float(raster_data[r - 1, c + 1])

    z21 = float(raster_data[r, c - 1])
    z22 = float(raster_data[r, c])
    z23 = float(raster_data[r, c + 1])

    z31 = float(raster_data[r + 1, c - 1])
    z32 = float(raster_data[r + 1, c])
    z33 = float(raster_data[r + 1, c + 1])

    # Replace NaNs with 0.0 to avoid propagation
    z11 = 0.0 if math.isnan(z11) else z11
    z12 = 0.0 if math.isnan(z12) else z12
    z13 = 0.0 if math.isnan(z13) else z13
    z21 = 0.0 if math.isnan(z21) else z21
    z22 = 0.0 if math.isnan(z22) else z22
    z23 = 0.0 if math.isnan(z23) else z23
    z31 = 0.0 if math.isnan(z31) else z31
    z32 = 0.0 if math.isnan(z32) else z32
    z33 = 0.0 if math.isnan(z33) else z33

    # Cell sizes in degrees
    cellsize_x = abs(transform.a)
    cellsize_y = abs(transform.e)

    # Convert to meters based on local latitude
    lat_rad = math.radians(lat)
    dx = cellsize_x * 111320.0 * math.cos(lat_rad)
    dy = cellsize_y * 111320.0

    # Horn's algorithm for slope calculation
    dz_dx = ((z13 + 2.0 * z23 + z33) - (z11 + 2.0 * z21 + z31)) / (8.0 * dx)
    dz_dy = ((z31 + 2.0 * z32 + z33) - (z11 + 2.0 * z12 + z13)) / (8.0 * dy)

    slope_rise_run = math.sqrt(dz_dx**2 + dz_dy**2)
    slope_deg = math.degrees(math.atan(slope_rise_run))
    return slope_deg


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
