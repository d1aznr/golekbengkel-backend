# GolekBengkel Backend

Backend API untuk pencarian rute bengkel terdekat di Kabupaten Tuban dengan mempertimbangkan waktu tempuh berbasis medan (terrain-aware travel time) menggunakan graf berbobot berarah dan algoritma Dijkstra.

## Fitur Utama

* **Directed Weighted Graph** — Pemodelan graf berarah dengan atribut jalan dari OSM (`highway`, `surface`) dan elevasi DEMNAS.
* **Terrain-Aware Travel Time** — Edge cost berupa waktu tempuh aktual berdasarkan model kecepatan berbasis medan.
* **Slope Multiplier** — Skalar kemiringan untuk memodelkan kesulitan medan (misalnya mendorong motor), dengan nilai default `3.0`.
* **DEMNAS Integration** — Data elevasi resolusi tinggi (~8 meter) dari DEM Nasional, termasuk perhitungan terrain slope menggunakan Horn's Method.
* **Road Type Classification** — Tag OSM `highway` dan `surface` diklasifikasikan menjadi `paved_road` atau `unpaved_road` untuk model GLM.
* **Spatial Indexing** — Pencarian node terdekat menggunakan SciPy KDTree dengan kompleksitas rata-rata `O(log N)`.
* **Swagger Documentation** — Dokumentasi API interaktif tersedia di `/apidocs`.

### Travel Time Cost

```text
T = d / (v_eff / 3.6)
```

Keterangan:

* `T` = waktu tempuh (detik)
* `d` = panjang edge (meter)
* `v_eff` = kecepatan efektif (km/jam)

## Velocity Models

### GLM (Wood et al., 2023)

```text
v = exp(a + b·φ_eff + c·θ_eff + d·θ_eff²)
```

### Tobler Hiking Function

```text
v = 6 · exp(-3.5 · |s_eff + 0.05|)
```

### Naismith Rule

```text
v = 5 · d / (d + 8.333 · max(0, Δh_eff))
```

## Slope Multiplier

Semua model menggunakan faktor pengali kemiringan untuk menskalakan efek medan.

```text
θ_eff = arctan(k · tan(θ))
s_eff = k · s
Δh_eff = k · Δh
```

Keterangan:

* `k` = `slope_multiplier`
* `θ` = sudut kemiringan asli (radian)
* `s` = grade/slope asli
* `Δh` = perubahan elevasi asli

## Tech Stack

* Python 3 + Flask
* NetworkX (Graph + Dijkstra)
* Flasgger (Swagger/OpenAPI)
* Rasterio (DEMNAS DEM)
* GeoPandas (GeoJSON Roads)
* SciPy KDTree (Nearest-Node Lookup)

## Quick Start

```bash
# Setup environment + install dependencies
chmod +x setup.sh run.sh
./setup.sh

# Start the API server
./run.sh
```

Swagger UI:

```text
http://localhost:5000/apidocs
```

## API Endpoints

| Method | Path                | Description                                                     |
| ------ | ------------------- | --------------------------------------------------------------- |
| `POST` | `/api/route`        | Cari rute optimal berdasarkan waktu tempuh atau jarak terpendek |
| `GET`  | `/api/nearest-node` | Cari node graf terdekat                                         |
| `GET`  | `/api/graph-info`   | Statistik graf                                                  |
| `GET`  | `/health`           | Health check                                                    |

## Contoh Request: Find Route

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

## Parameter

| Parameter          | Type         | Default    | Deskripsi                                                                     |
| ------------------ | ------------ | ---------- | ----------------------------------------------------------------------------- |
| `start`            | `[lat, lon]` | *required* | Koordinat awal                                                                |
| `end`              | `[lat, lon]` | *required* | Koordinat tujuan                                                              |
| `mode`             | `string`     | `"time"`   | `"time"` untuk waktu tempuh atau `"distance"` untuk jarak terpendek           |
| `model`            | `string`     | `"glm"`    | Model kecepatan: `"glm"`, `"tobler"`, atau `"naismith"`                       |
| `slope_multiplier` | `float`      | `3.0`      | Faktor pengali kemiringan                                                     |
| `ignore_downhill`  | `bool`       | `false`    | Abaikan aturan kecepatan turun konstan 5 km/jam                               |
| `lambda`           | `float`      | `null`     | Backward compatibility. Jika > 0 akan diperlakukan sebagai `slope_multiplier` |

## Response

Response menyertakan:

* `travel_time` (detik)
* `slope_characteristics` (statistik kemiringan rute)
* Parameter model yang digunakan
* Informasi rute dan node

## Backward Compatibility

Parameter `lambda` lama masih diterima.

Jika:

```text
lambda > 0
```

maka nilainya akan digunakan sebagai:

```text
slope_multiplier = lambda
```

Jika tidak ada parameter baru yang dikirim, sistem menggunakan konfigurasi default:

```text
mode = "time"
model = "glm"
slope_multiplier = 3.0
```

## Project Structure

```text
├── app.py                  # Flask app entry point + Swagger docs
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── setup.sh
├── run.sh
├── test_routing.py         # Tests
├── data/                   # GeoJSON, DEM, graph
├── preprocessing/
│   ├── build_graph.py      # GeoJSON + DEM → graph.pkl
│   ├── elevation.py        # DEM elevation sampling + Horn terrain slope
│   └── slope.py            # Haversine + slope calculation
├── core/
│   ├── graph_loader.py     # Load/cache graph
│   ├── cost.py             # Velocity models + travel time cost
│   └── routing.py          # Dijkstra + KDTree + slope statistics
└── api/
    ├── routes.py           # Endpoints + Swagger docs
    └── schemas.py          # Request validation
```
