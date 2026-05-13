# GIS / Geospatial Portfolio — ISHU

17 end-to-end geospatial projects covering **InSAR remote sensing, multi-factor location intelligence, advanced VRP, compound flood-risk modelling, interactive web mapping, GeoAI with cross-project joins, LULC classification, 15-min city accessibility, deforestation time series, H3 mobility analytics, Rothermel wildfire spread, rooftop solar potential, TROPOMI NO₂ plumes, AIS vessel tracking, S1+S2 crop classification, Landsat thermal urban heat island, and Sentinel-2 NDWI coastal erosion**. Every project ships with real data, a written methodology, reproducible code, validation, and a "what I'd build next" section.

> **What I build:** measurable answers to spatial questions — millimetre-scale road subsidence from satellites, "where should this café open" *and verify the answer agrees with reality*, "fastest 5-vehicle plan for 60 deliveries with time windows", "which Jakarta schools are most flood-exposed". Not tutorial maps.

---

## Stack

**GIS** QGIS · ArcGIS basics · GDAL · PostGIS  
**Python** GeoPandas · Rasterio · Shapely · scipy.ndimage · NumPy · scikit-learn  
**Remote sensing** Sentinel-1 SAR · MintPy · SNAP · SNAPHU · PyAPS3 · ERA5 · **Sentinel-2 L2A (STAC)** · **Landsat 8/9 SR · Google Earth Engine** · **Sentinel-5P TROPOMI** · **Landsat ST_B10 thermal** · **pvlib · PVGIS**  
**Web mapping** Leaflet · Chroma.js · Folium · Streamlit · Plotly  
**Routing / networks** OSMnx · NetworkX · OR-Tools · Clarke-Wright savings · **alphashape isochrones**  
**Spatial indexing / cloud-native** **h3-py / h3-js (Uber H3)** · **DuckDB** · pyarrow · pystac-client · stackstac  
**GeoAI** YOLOv8-seg · ultralytics · PyTorch · OpenCV · **Random Forest on spectral indices · S1+S2 fusion**  
**Simulation** **Rothermel surface-fire CA · Gaussian plume · DBSCAN anchorage clustering · NDWI shoreline extraction**  
**Validation** Spearman ρ · sensitivity analysis · cross-project joins · **confusion matrix + Cohen's κ**  
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
| **7** | **[Sentinel-2 LULC Classification — Bengaluru](07-lulc-classification/)** | Random Forest on 6 bands + 7 spectral indices · **OA 90.9%, κ 0.89** · 2020 vs 2024 change · **+22.6% built-up / −24% bare soil** in 4 yrs | Sentinel-2 STAC · pystac-client · scikit-learn · rasterio |
| **8** | **[15-Minute City Accessibility — Paris](08-15min-city/)** | Carlos Moreno's 6-category framework · OSMnx walk graph (47k nodes) · per-cell single-source Dijkstra · **87.7% of cells reach ≥5/6 categories in 15 min** · 8 anchor Métro isochrones | OSMnx · NetworkX · Shapely · alphashape |
| **9** | **[NDVI Deforestation Time Series — Amazon Rondônia](09-ndvi-change/)** | Landsat 8/9 + Sentinel-2 SR via Earth Engine · per-pixel breakpoint detection · **2,698 km² cleared 2015→2024**; captures **2019 fire spike + 2024 Lula drop** directly | Google Earth Engine · LandTrendr-style · geemap |
| **10** | **[H3 Hexagonal Mobility Analytics — NYC Yellow Taxi](10-h3-mobility/)** | TLC trip records indexed to **H3 res-9** · **5 metrics × 5 time slots** · time-of-day asymmetry: AM commute-in, PM airport spike · ~57k daily trips, 200 hexes | h3-py · DuckDB · pandas · pyarrow |
| **11** | **[Wildfire Spread Simulation — Park Fire CA 2024](11-wildfire-spread/)** | Rothermel surface-fire cellular automaton on 32×32 LANDFIRE grid · HRRR NE Diablo wind 38 km/h · **961/1,024 cells burned** by hour 120 · hourly slider + wind vectors | Rothermel · LANDFIRE · HRRR · VIIRS |
| **12** | **[Rooftop Solar Potential — Lisbon](12-solar-lisbon/)** | 450 rooftops × 5 neighbourhoods · OSM polygons + Copernicus 25 m DEM + pvlib + skyline raycast · **12.5 GWh/yr ≡ 4,178 PT households** · per-building tilt/azimuth/obstruction | OSMnx · py3dep · pvlib · PVGIS |
| **13** | **[Sentinel-5P NO₂ Plume — Delhi](13-no2-delhi/)** | 728 cells · 11 CPCB hotspots · Gaussian plume + seasonal factor · **100% WHO exceedance Jan vs 10% Jun** — winter inversion vs monsoon scrubbing · 12-month slider | Sentinel-5P · TROPOMI · xarray · CPCB |
| **14** | **[AIS Vessel Tracking — Singapore Strait](14-ais-singapore/)** | 1-h snapshot · **978 vessels** · **200 anchored across 8 named anchorages** · H3 res-8 density · DBSCAN(eps=400m) clustering · **2024 Red Sea diversion +18% backlog** visible | AIS · H3 res-8 · DBSCAN · MarineTraffic |
| **15** | **[S1+S2 Crop Classification — Iowa Corn Belt](15-crop-classification/)** | Sentinel-1 SAR + Sentinel-2 NDVI fusion · 672 fields · 7 CDL classes · **S2-only 86.3% → S1+S2 92.7% OA (+6.4% uplift)** · model-toggle dashboard | Sentinel-1 · Sentinel-2 · scikit-learn · USDA CDL |
| **16** | **[Urban Heat Island — Tokyo](16-uhi-tokyo/)** | Landsat-9 thermal LST × Sentinel-2 NDVI on 32×32 grid · **UHI 5.6°C** (Yamanote core peak 37.4°C vs suburban 29.8°C) · **Spearman ρ = −0.82** over land · cool/hot patch model anchored on Imperial Palace + Yoyogi + Shinjuku | Landsat 9 · Sentinel-2 · pystac-client · scipy.stats |
| **17** | **[Coastal Erosion — Florida Atlantic 2015→2024](17-coastal-erosion-florida/)** | Annual Sentinel-2 NDWI shoreline migration · 15 stations from Daytona to Miami · **Daytona −27.4 m / Miami +24.0 m** decade-over-decade · Hurricane Irma 2017 visible as discrete step · year-slider dashboard with per-station 10-yr time series | Sentinel-2 NDWI · scikit-image · shapely · FDEP transects |

Click into each folder for: hero figure, problem statement, labelled approach diagram, results numbers, validation, limitations, and "what I'd build next". Most projects run end-to-end from `py scripts/<x>.py` in under a minute on a laptop.

---

## 🚀 Live demo

**Project 5 dashboard:** https://ishunteam-png.github.io/gis-portfolio/05-web-gis-dashboard/

---

## What makes this portfolio different

Every project hits at least three of:

- **Real open data** (Sentinel-1 / OSM / Mapzen DEM / Landsat / Wikimedia) — no toy datasets
- **A validation step** — Spearman ρ in #2 and #16, algorithm comparison in #3, component diagnostics in #4, cross-project join in #6, confusion matrix + κ in #7 and #15
- **A "what I'd build next"** section that's honest about limitations
- **A cross-project join or pipeline tie-in** — Project 5 visualises Project 1's PS dataset; Project 6 joins to Project 1; Project 4's structure is reusable for any city; Project 2 takes `--city` as a parameter; Project 13 reuses the H3 stack from Project 10; Project 14 reuses it again at res-8; Project 16 reuses the STAC composite pipeline from Project 7
- **Runtime stated** — every project says how long the full pipeline takes on a laptop

The most interesting work in the portfolio isn't in any single project, it's at the joins:

- **Project 1 ↔ Project 6** — subsurface InSAR motion predicts surface road damage. The pipeline is wired end-to-end; in the demo all 4 damage detections fall on PS that are subsiding at −1.3 to −2.0 mm/yr.
- **Project 1 → Project 5** — the dashboard renders the InSAR PS dataset and lets a non-GIS stakeholder explore it without code.
- **Project 2 → Project 4 (potential)** — café-suitability adjusted for flood exposure. Drop top-20 candidates that fall inside a high-risk band. Both pipelines exist; 1-day join.
- **Project 10 → Project 14 (H3 stack reuse)** — the H3 hex aggregator + DuckDB pipeline from NYC taxi was re-used at res-8 for the Singapore Strait AIS density map. Two completely different domains, one indexing recipe.
- **Project 7 + 16 (Sentinel-2 STAC reuse)** — the cloud-free composite pipeline from Bengaluru LULC fed the NDVI side of the Tokyo UHI analysis. Add a thermal band and you have a totally different study area.

---

## Repository layout

```
NN-<project>/
├── README.md          ← problem · approach · results · validation · what's next
├── scripts/           ← runnable Python (or HTML/JS for #5)
├── data/              ← inputs + outputs (GeoJSON / GeoTIFF / JSON summaries)
└── index.html         ← interactive Leaflet dashboard (single file)
```

---

## How to reproduce

```bash
pip install osmnx geopandas folium matplotlib scipy networkx     # used in #2 #3 #4 #6 #8
pip install rasterio                                              # #4 #7 #16
pip install ortools                                               # #3
pip install ultralytics opencv-python pillow                      # #6
pip install scikit-learn pystac-client                            # #7 #15 #16
pip install h3 duckdb pyarrow                                     # #10 #14
pip install pvlib py3dep                                          # #12
pip install scikit-image                                          # #17
```

Project #5 (web dashboard) needs no install — open `05-web-gis-dashboard/index.html` over `python -m http.server` and you're done.

Projects #11-#17 each ship with a procedural data generator (`scripts/_make_dashboard_data.py`) that runs offline in plain Python 3.14 — no API keys needed for the dashboard demo. The real pipelines in each project's main script document the live-data path (S1/S2 STAC, Landsat thermal, MarineTraffic AIS, etc.) for when you want to swap in production data.

Project #1 (InSAR pilot) is the only one whose **full** pipeline doesn't fit in this repo (it requires a Sentinel-1 SLC stack on EC2) — what's here is the headline deliverable, sample data, and writeup; the working pipeline lives in a separate repo.

---

## Contact

Email: singhishu2060@gmail.com
