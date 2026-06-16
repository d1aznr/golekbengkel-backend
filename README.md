# GolekBengkel Backend

Backend API untuk pencarian rute bengkel terdekat di Kabupaten Tuban dengan mempertimbangkan waktu tempuh berbasis medan (terrain-aware travel time) menggunakan graf berbobot berarah dan algoritma Dijkstra.

## Fitur Utama

- **Directed Weighted Graph** — Pemodelan graf berarah dengan atribut jalan dari OSM (highway, surface) dan elevasi DEMNAS.
- **Terrain-Aware Travel Time** — Edge cost berupa waktu tempuh aktual (`T = d / (v_eff / 3.6)`) dengan tiga model kecepatan: GLM, Tobler, Naismith.
- **Slope Multiplier** — Skalar kemiringan untuk memodelkan kesulitan medan (misalnya mendorong motor), dengan default `3.0`.
- **DEMNAS Integration** — Data elevasi resolusi tinggi (~8 meter) dari DEM Nasional, termasuk perhitungan terrain slope menggunakan Horn's method.
- **Road Type Classification** — OSM `highway` dan `surface` tags diklasifikasikan menjadi `paved_road` / `unpaved_road` untuk model GLM.
- **Spatial Indexing** — Pencarian node terdekat menggunakan SciPy KDTree untuk performa O(log N).
- **Swagger Documentation** — Dokumentasi API interaktif di `/apidocs`.

## Velocity Models

| Model | Formula | Source |
|-------|---------|--------|
| **GLM** | `v = exp(a + b·φ_eff + c·θ_eff + d·θ_eff²)` | Wood et al., 2023 |
| **Tobler** | `v = 6 · exp(-3.5 · |s_eff + 0.05|)` | Classic hiking function |
| **Naismith** | `v = 5 · d / (d + 8.333 · max(0, Δh_eff))` | Rule of thumb |

Semua model menggunakan slope multiplier untuk menskalakan input kemiringan:
- θ_eff = arctan(k · tan(θ))
- s_eff = k · s
- Δh_eff = k · Δh

## Tech Stack

- Python 3 + Flask
- NetworkX (graf + Dijkstra)
- Flasgger (Swagger/OpenAPI)
- Rasterio (DEMNAS DEM)
- GeoPandas (GeoJSON roads)
- SciPy KDTree (nearest-node lookup)

## Quick Start

```bash
# Setup environment + install dependencies
chmod +x setup.sh run.sh
./setup.sh

# Start the API server
./run.sh
```

Swagger UI: [http://localhost:5000/apidocs](http://localhost:5000/apidocs)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/route` | Cari rute optimal berdasarkan waktu tempuh atau jarak terpendek |
| `GET` | `/api/nearest-node` | Cari node graf terdekat |
| `GET` | `/api/graph-info` | Statistik graf |
| `GET` | `/health` | Health check |

### Contoh Request: Find Route

```bash
curl -X POST http://localhost:5000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "start": [-6.9, 112.0],
    "end": [-6.915, 112.03],
    "mode": "time",
    "model": "glm",
    "slope_multiplier": 3.0,
    "ignore_downhill": false
  }'
```

#### Parameter

| Parameter | Type | Default | Deskripsi |
|-----------|------|---------|-----------|
| `start` | `[lat, lon]` | *required* | Koordinat awal |
| `end` | `[lat, lon]` | *required* | Koordinat tujuan |
| `mode` | `string` | `"time"` | `"time"` (waktu tempuh) atau `"distance"` (jarak terpendek) |
| `model` | `string` | `"glm"` | Model kecepatan: `"glm"`, `"tobler"`, atau `"naismith"` |
| `slope_multiplier` | `float` | `3.0` | Skalar kemiringan untuk simulasi beban/mendorong |
| `ignore_downhill` | `bool` | `false` | Abaikan aturan kecepatan turun konstan 5 km/h |
| `lambda` | `float` | `null` | Backward compatibility — jika diisi > 0, dijadikan `slope_multiplier` |

#### Response

Response sekarang menyertakan `travel_time` (detik), `slope_characteristics` (statistik kemiringan), dan parameter yang digunakan.

### Backward Compatibility

Parameter `lambda` lama masih diterima. Jika `lambda > 0`, nilainya digunakan sebagai `slope_multiplier`. Jika tidak ada parameter baru yang dikirim, default adalah mode `"time"` dengan model `"glm"`.

## Project Structure

```
├── app.py                  # Flask app entry point + Swagger docs
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── setup.sh / run.sh       # Scripts
├── test_routing.py         # Tests
├── data/                   # GeoJSON, DEM, graph
├── preprocessing/          # Graph building pipeline
│   ├── build_graph.py      # GeoJSON + DEM → graph.pkl (dengan road type & terrain slope)
│   ├── elevation.py        # DEM elevation sampling + Horn's terrain slope
│   └── slope.py            # Haversine + walking slope calc
├── core/                   # Routing logic
│   ├── graph_loader.py     # Load/cache graph
│   ├── cost.py             # Velocity models (GLM, Tobler, Naismith) + travel time cost
│   └── routing.py          # Dijkstra + KDTree + slope characteristics
└── api/                    # REST API
    ├── routes.py           # Endpoints + Swagger docs
    └── schemas.py          # Pydantic validation (mode, model, slope_multiplier, dll.)
```
