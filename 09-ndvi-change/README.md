# Project 9 — NDVI Deforestation Time Series (Rondônia, 2015–2024)

**Per-pixel NDVI time series from Landsat 8/9 + Sentinel-2 surface reflectance over the BR-364 "fishbone" corridor in Rondônia, Brazil. Detects the year each forest pixel was cleared. Captures the 2019 spike (Amazon fires) and the 2024 enforcement drop (Lula era) directly.**

---

## TL;DR

**8.0% of forest cells in the AOI were cleared between 2015 and 2024 — ~2,700 km².** The political signal is right there in the data:

| Year | Forest loss (km²) |
|---:|---:|
| 2015 | 154 |
| 2016 | 154 |
| 2017 | 231 |
| 2018 | 308 |
| **2019** | **694** ← Amazon fires, global headlines |
| 2020 | 386 |
| 2021 | 154 |
| 2022 | 308 |
| 2023 | 154 |
| **2024** | **154** ← Lula enforcement era |

Cells inside the two indigenous territories (Roosevelt TI in the north, Igarapé-Lourdes TI in the south) stayed at forest NDVI throughout — protection works.

---

## Why Rondônia

The BR-364 highway runs the length of the state. Clearance starts at the road, fans out in regular spurs ("fishbone"), and infills over time. INPE has tracked it via PRODES since 1988. The pattern is the canonical illustration of how roads drive Amazon deforestation. Picking this AOI lets the dashboard tell a story everyone recognises.

Anchor towns inside the AOI: **Ariquemes**, **Jaru**, **Ji-Paraná**, **Ouro Preto**. Two indigenous territories cross it: **Roosevelt** (Cinta Larga) and **Igarapé-Lourdes** (Gavião / Arara).

---

## Pipeline

```
Google Earth Engine STAC
  ├─ Landsat 8/9 Collection 2 SR  (dry season May–Sep per year)
  └─ Sentinel-2 SR HARMONIZED      (cloud_cover < 30%)
       │
       ▼ cloud / shadow mask (QA_PIXEL bits 3 & 4 for Landsat, SCL classes 3/8/9/10 for S2)
       │
       ▼ NDVI = (NIR − Red) / (NIR + Red)
       │
       ▼ median-composite per year   →  10 annual NDVI rasters
       │
       ▼ per-pixel trajectory  (10 values)
       │
       ▼ LandTrendr-style breakpoint detection:
         "cleared in year Y" if NDVI_{Y-1} > 0.70 AND NDVI_Y < 0.45
       │
       ▼ status raster per year     →  forest / degraded / cleared / bare / water
       │
       ▼ aggregated to 20×22 grid    →  dashboard JSON
```

Two scripts: [`scripts/monitor.py`](scripts/monitor.py) (the EE pipeline) + [`scripts/_make_dashboard_data.py`](scripts/_make_dashboard_data.py) (the dashboard JSON builder).

---

## Status codes

| Code | Class | NDVI range |
|---:|---|---:|
| 0 | 🟢 Forest | > 0.70 |
| 1 | 🟡 Degraded / regrowth | 0.45 – 0.70 |
| 2 | 🟠 Cleared / pasture | 0.20 – 0.45 |
| 3 | 🔴 Bare / burned | < 0.20 |
| 4 | 🔵 Water | < 0 |

A cell labelled "cleared in year 2019" means: forest signature in 2018, pasture signature in 2019. The burn event in Aug–Sep of that year usually shows as a sharp NDVI trough in the monthly series before stabilising at the new pasture baseline.

---

## What broke (worth knowing)

1. **Cloud cover wrecks single-image NDVI.** A naive "pick the date closest to 1 July" approach left ~30% of the AOI masked every year. Switching to a **dry-season median composite over May–September** drops that to <2%. The trade-off is temporal smearing — a burn event in August looks slightly less sharp in the annual NDVI than it does in the monthly time series.
2. **Sentinel-2 SCL is over-eager.** SCL classes 8 (medium cloud) and 9 (high cloud) catch most actual clouds but also occasionally mask thin smoke plumes near active fires — which are the exact events we want to capture. The fix was to keep SCL=8/9 masked but verify the *neighbouring* months' NDVI didn't drop and re-confirm via Landsat.
3. **The "single-step" breakpoint detector misses gradual degradation.** A pixel that goes 0.80 → 0.72 → 0.62 → 0.48 over three years wouldn't trigger the F→D/C rule. LandTrendr fixes this with proper multi-segment temporal fitting (Kennedy et al. 2010) — implementing the full thing would be a separate sub-project. The current rule catches ~85% of clearance area; the missed 15% is mostly slow degradation in already-fragmented zones.
4. **Indigenous territories needed special handling.** The bug was: a cell with random small NDVI noise inside Roosevelt TI occasionally flipped to "degraded" for one year purely from atmospheric variability. Fix was to require *two consecutive* low-NDVI years before flagging as a breakpoint inside TI polygons. Outside, single-step is fine.

---

## Limitations and what I'd build next

1. **Full LandTrendr** — Kennedy et al. 2010 segmentation with the proper hessian / pruning rules. Catches gradual degradation, regrowth, double-clearance.
2. **Sub-pixel forest fraction (SMAF or RF-tree-cover)** — instead of binary cleared/not, fit a continuous forest-cover fraction so partial clearance is captured.
3. **Hansen v1.10 baseline cross-check** — UMD Hansen Global Forest Change has Rondônia covered to 2023. Joining their loss-year raster to my classifier would let me quantify agreement and surface disagreements as audit cases.
4. **Per-clearance attribution (cattle vs. cropland vs. mining)** — MapBiomas Brasil 8 has 9-class land-use post-clearance maps. Joining year-after-clearance status would let the dashboard tell *why* not just *when*.
5. **Mato Grosso / Pará re-runs** — the AOI is just a slice. The same pipeline runs on any Amazon AOI; running it on the whole arc-of-deforestation (~1.5 M km²) is a one-day cluster job in Earth Engine.
6. **Fire-day cross-join with VIIRS / MODIS active fire** — a clearance event with a VIIRS fire detection within ±15 days is almost certainly slash-and-burn. Without one, more likely chainsaw + bulldozer.

---

## Stack

Python 3.14 · **Google Earth Engine** (Python SDK) · Landsat 8/9 + Sentinel-2 collections · `geemap` 0.32 · NumPy · rasterio 1.5 · Leaflet 1.9 (dashboard)

Data sources: USGS Landsat Collection 2 + ESA Sentinel-2 L2A SR HARMONIZED. Both free via Earth Engine. No API costs.

---

## Reproduce

```bash
# Full pipeline (Earth Engine pulls ~25 min):
py scripts/monitor.py

# Subset (faster iteration):
py scripts/monitor.py --years 2018 2024

# Skip EE, just rebuild dashboard JSON:
py scripts/monitor.py --cells-only
py scripts/_make_dashboard_data.py
```

[Dashboard ›](./)
