# GIS / Geospatial Portfolio — ISHU

End-to-end geospatial projects covering **InSAR remote sensing, multi-factor location intelligence, advanced VRP, compound flood-risk modelling, interactive web mapping, and GeoAI with cross-project joins**. Every project ships with real data, a written methodology, reproducible code, validation, and a "what I'd build next" section.

> **What I build:** measurable answers to spatial questions — millimetre-scale road subsidence from satellites, "where should this café open" *and verify the answer agrees with reality*, "fastest 5-vehicle plan for 60 deliveries with time windows", "which Jakarta schools are most flood-exposed". Not tutorial maps.

---

## Stack

**GIS** QGIS · ArcGIS basics · GDAL · PostGIS  
**Python** GeoPandas · Rasterio · Shapely · scipy.ndimage · NumPy · scikit-learn  
**Remote sensing** Sentinel-1 SAR · MintPy · SNAP · SNAPHU · PyAPS3 · ERA5  
**Web mapping** Leaflet · Chroma.js · Folium · Streamlit · Plotly  
**Routing / networks** OSMnx · NetworkX · OR-Tools · Clarke-Wright savings  
**GeoAI** YOLOv8-seg · ultralytics · PyTorch · OpenCV  
**Validation** Spearman ρ · sensitivity analysis · cross-project joins  
**Infra** AWS EC2 · S3 · Docker

---

## Projects

| # | Project | Headline | Tech |
|---|---|---|---|
| **1** | **[InSAR Road Subsidence — Delhi](01-insar-road-subsidence/)** | 2,555 PS · V_U −10.3 to +4.7 mm/yr · strict EGMS-L3 · 2D V_U + V_E decomposition · $1 AWS cost | Sentinel-1 · MintPy · SNAP · PyAPS3 |
| **2** | **[Real Estate Location Intelligence — Tbilisi (any city via `--city`)](02-real-estate-intel/)** | 8,415 cells over 504 km² · **5 signals incl. walkability (62,849 intersections)** · **validated Spearman ρ = 0.39 vs real cafés** | OSMnx · GeoPandas · scipy.stats · Folium |
| **3** | **[Advanced Capacitated VRP w/ Time Windows — Tbilisi](03-route-optimization/)** | 60 stops · 5 vehicles · 3 windows · capacity 20 · **3 algorithms compared** (greedy / Clarke-Wright 1964 / OR-Tools) · OR-Tools **−20.3 %** vs greedy · fleet-size sensitivity sweep | OSMnx · NetworkX · OR-Tools |
| **4** | **[Jakarta Compound Flood Risk (multi-factor)](04-flood-risk/)** | World's most flood-prone megacity · **4-factor risk index** (HAND + slope + drainage density + imperviousness) · **1,360 schools + 138 hospitals exposed** to high+VH risk | rasterio · scipy.ndimage · OSMnx |
| **5** | **[Web GIS Dashboard — Delhi PS](05-web-gis-dashboard/)** | Single-file Leaflet · 2,656 PS · **6 presets, split view, live histogram, URL hash state** for shareable views | Leaflet · Chroma.js · vanilla JS |
| **6** | **[GeoAI Road Damage + Cross-Project Join to Project 1](06-geoai-road-damage/)** | YOLOv8m-seg · **mask-area severity** (not bbox) · **all 4 detections land on subsiding PS** — operationalises the InSAR→damage causal chain | ultralytics · PyTorch · OpenCV · GeoPandas |

Click into each folder for: hero figure, problem statement, labelled approach diagram, results numbers, validation, limitations, and "what I'd build next". Most projects run end-to-end from `py scripts/<x>.py` in under a minute on a laptop.

---

## 🚀 Live demo

**Project 5 dashboard:** https://ishunteam-png.github.io/gis-portfolio/05-web-gis-dashboard/

---

## What makes this portfolio different

Every project hits at least three of:

- **Real open data** (Sentinel-1 / OSM / Mapzen DEM / Wikimedia) — no toy datasets
- **A validation step** — Spearman ρ in #2, algorithm comparison in #3, component diagnostics in #4, cross-project join in #6
- **A "what I'd build next"** section that's honest about limitations
- **A cross-project join or pipeline tie-in** — Project 5 visualises Project 1's PS dataset; Project 6 joins to Project 1; Project 4's structure is reusable for any city; Project 2 takes `--city` as a parameter
- **Runtime stated** — every project says how long the full pipeline takes on a laptop

The most interesting work in the portfolio isn't in any single project, it's at the joins:

- **Project 1 ↔ Project 6** — subsurface InSAR motion predicts surface road damage. The pipeline is wired end-to-end; in the demo all 4 damage detections fall on PS that are subsiding at −1.3 to −2.0 mm/yr.
- **Project 1 → Project 5** — the dashboard renders the InSAR PS dataset and lets a non-GIS stakeholder explore it without code.
- **Project 2 → Project 4 (potential)** — café-suitability adjusted for flood exposure. Drop top-20 candidates that fall inside a high-risk band. Both pipelines exist; 1-day join.

---

## Repository layout

```
0X-<project>/
├── README.md          ← problem · approach · results · validation · what's next
├── scripts/           ← runnable Python (or HTML/JS for #5)
├── data/              ← inputs + outputs (GeoJSON / GeoTIFF / JSON summaries)
└── assets/            ← hero images, charts, interactive HTML, screenshots
```

---

## How to reproduce

```bash
pip install osmnx geopandas folium matplotlib scipy networkx     # used in #2 #3 #4 #6
pip install rasterio                                              # #4
pip install ortools                                               # #3
pip install ultralytics opencv-python pillow                      # #6
```

Project #5 (web dashboard) needs no install — open `05-web-gis-dashboard/index.html` over `python -m http.server` and you're done.

Project #1 (InSAR pilot) is the only one whose **full** pipeline doesn't fit in this repo (it requires a Sentinel-1 SLC stack on EC2) — what's here is the headline deliverable, sample data, and writeup; the working pipeline lives in a separate repo.

---

## Contact

Email: singhishu2060@gmail.com
