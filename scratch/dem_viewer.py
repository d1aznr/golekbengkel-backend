import os
import sys
from pathlib import Path
import math

# Menambahkan root project ke sys.path agar bisa import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, request, send_file, render_template_string
import rasterio
import numpy as np

from PIL import Image
from config import DEMNAS_TIF

app = Flask(__name__)

# Cache the dataset transform and bounds
_dataset = None
_raster_data = None
_bounds = None
_transform = None

def get_raster():
    global _dataset, _raster_data, _bounds, _transform
    if _dataset is None:
        _dataset = rasterio.open(DEMNAS_TIF)
        _raster_data = _dataset.read(1)
        _bounds = _dataset.bounds
        _transform = _dataset.transform
    return _dataset, _raster_data, _bounds, _transform

def generate_dem_preview():
    preview_path = Path(__file__).parent / "dem_preview.png"
    if preview_path.exists():
        return preview_path
        
    print("Generating DEM preview image...")
    src, data, bounds, transform = get_raster()
    
    # Downsample untuk preview (Leaflet overlay)
    scale = 5
    out_shape = (data.shape[0] // scale, data.shape[1] // scale)
    
    # Baca ulang dengan downsampling
    data_small = src.read(1, out_shape=out_shape)
    
    # Identifikasi NaN
    mask = np.isnan(data_small)
    data_clean = np.nan_to_num(data_small, nan=0.0)
    
    # Normalisasi (hindari membagi dengan 0)
    min_val, max_val = np.nanmin(data), np.nanmax(data)
    if max_val == min_val:
        norm_data = np.zeros_like(data_clean)
    else:
        norm_data = (data_clean - min_val) / (max_val - min_val)
        
    # Grayscale mapping (0-255)
    gray_img = (norm_data * 255).astype(np.uint8)
    
    # Buat array RGBA (karena kita butuh alpha channel)
    rgba = np.zeros((data_small.shape[0], data_small.shape[1], 4), dtype=np.uint8)
    rgba[..., 0] = gray_img  # R
    rgba[..., 1] = gray_img  # G
    rgba[..., 2] = gray_img  # B
    rgba[..., 3] = 255       # A (Full opacity default)
    
    # Set area NaN menjadi transparan
    rgba[mask, 3] = 0  # Alpha = 0
    
    img = Image.fromarray(rgba, 'RGBA')
    img.save(preview_path)
    print(f"Preview saved to {preview_path}")
    
    return preview_path

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DEMNAS Viewer</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { margin: 0; padding: 0; }
        #map { width: 100vw; height: 100vh; }
        .info-box {
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
            font-family: Arial, sans-serif;
        }
    </style>
</head>
<body>
    <div class="info-box">
        <strong>DEMNAS Viewer</strong><br>
        Klik di mana saja pada peta (terutama di area overlay warna)<br>
        untuk melihat nilai elevasi sebenarnya dari file raster.
    </div>
    <div id="map"></div>

    <script>
        // Init Map
        var map = L.map('map').setView([{{ center_lat }}, {{ center_lon }}], 11);

        // OpenStreetMap Basemap
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        // DEM Image Overlay
        var imageUrl = '/dem-image';
        var imageBounds = [[{{ min_lat }}, {{ min_lon }}], [{{ max_lat }}, {{ max_lon }}]];
        L.imageOverlay(imageUrl, imageBounds, {opacity: 0.7}).addTo(map);
        
        map.fitBounds(imageBounds);

        var marker = null;

        // Click Event
        map.on('click', function(e) {
            var lat = e.latlng.lat;
            var lon = e.latlng.lng;
            
            // Set temporary popup
            var popup = L.popup()
                .setLatLng(e.latlng)
                .setContent("Mengambil data elevasi...")
                .openOn(map);
                
            if (marker) map.removeLayer(marker);
            marker = L.marker(e.latlng).addTo(map);

            // Fetch Elevation from API
            fetch(`/api/elevation?lat=${lat}&lon=${lon}`)
                .then(response => response.json())
                .then(data => {
                    var elevText = data.elevation !== null ? data.elevation.toFixed(2) + ' meter' : 'NaN (Tidak ada data / Laut)';
                    var content = `<b>Koordinat:</b><br>${lat.toFixed(6)}, ${lon.toFixed(6)}<br><br><b>Elevasi DEMNAS:</b><br>${elevText}`;
                    popup.setContent(content);
                })
                .catch(err => {
                    popup.setContent("Error mengambil data");
                });
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    src, data, bounds, transform = get_raster()
    # bounds = (left/min_lon, bottom/min_lat, right/max_lon, top/max_lat)
    min_lon, min_lat, max_lon, max_lat = bounds.left, bounds.bottom, bounds.right, bounds.top
    
    return render_template_string(
        HTML_TEMPLATE,
        center_lat=(min_lat + max_lat) / 2,
        center_lon=(min_lon + max_lon) / 2,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon
    )

@app.route("/dem-image")
def dem_image():
    preview_path = generate_dem_preview()
    return send_file(preview_path, mimetype='image/png')

@app.route("/api/elevation")
def get_elevation():
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    
    src, data, bounds, transform = get_raster()
    
    # Konversi lat/lon ke pixel col/row
    col, row = ~transform * (lon, lat)
    col, row = int(col), int(row)
    
    # Cek bounds
    if 0 <= col < data.shape[1] and 0 <= row < data.shape[0]:
        val = data[row, col]
        if math.isnan(val):
            elev = None
        else:
            elev = float(val)
    else:
        elev = None
        
    return jsonify({"lat": lat, "lon": lon, "elevation": elev})

if __name__ == "__main__":
    print("Menyiapkan dataset DEMNAS...")
    get_raster()  # Pre-load raster
    generate_dem_preview() # Pre-generate image
    
    print("Membuka server di http://localhost:5002")
    app.run(host="0.0.0.0", port=5002, debug=True)
