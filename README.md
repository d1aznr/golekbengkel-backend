# GolekBengkel Backend

Backend API untuk pencarian rute bengkel terdekat di Kabupaten Tuban dengan mempertimbangkan kemiringan lereng (slope) menggunakan graf berbobot berarah dan algoritma Dijkstra.

## Fitur Utama

- **Directed Weighted Graph** — Pemodelan graf berarah untuk menangani biaya perjalanan asimetris (energi tanjakan > turunan).
- **Dynamic Anisotropic Cost Function** — Mengimplementasikan `Cost(u,v) = d(u,v) × (1 + λ × s⁺)` di mana λ (uphill penalty) dapat diatur secara dinamis via slider di frontend.
- **DEMNAS Integration** — Data elevasi menggunakan resolusi tinggi (~8 meter) dari DEM Nasional untuk perhitungan kemiringan lereng yang akurat.
- **Spatial Indexing** — Pencarian node terdekat menggunakan SciPy KDTree untuk performa O(log N).
- **Swagger Documentation** — Dokumentasi API interaktif yang sesuai standar industri di `/apidocs`.

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
| `POST` | `/api/route` | Find optimal route with dynamic λ |
| `GET` | `/api/nearest-node` | Find nearest graph node |
| `GET` | `/api/graph-info` | Graph statistics |
| `GET` | `/health` | Health check |

### Contoh Request: Find Route

```bash
curl -X POST http://localhost:5000/api/route \
  -H "Content-Type: application/json" \
  -d '{
    "start": [-6.9, 112.0],
    "end": [-6.95, 112.05],
    "lambda": 15.5
  }'
```

Parameter `lambda` menerima nilai float (misalnya dari slider UI). Nilai `0` berarti pencarian rute terpendek biasa, sedangkan nilai yang lebih tinggi (misal `10-100`) akan memaksa algoritma menghindari tanjakan curam.

## Project Structure

```
├── app.py                  # Flask app entry point
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── setup.sh / run.sh       # Scripts
├── test_routing.py         # Tests
├── data/                   # GeoJSON, DEM, graph
├── preprocessing/          # Graph building pipeline
│   ├── build_graph.py      # GeoJSON + DEM → graph.pkl
│   ├── elevation.py        # DEM elevation sampling
│   └── slope.py            # Haversine + slope calc
├── core/                   # Routing logic
│   ├── graph_loader.py     # Load/cache graph
│   ├── cost.py             # Dynamic cost function
│   └── routing.py          # Dijkstra + KDTree
└── api/                    # REST API
    ├── routes.py           # Endpoints + Swagger docs
    └── schemas.py          # Pydantic validation
```
