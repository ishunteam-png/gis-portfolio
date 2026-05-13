# Project 7 — Sentinel-2 LULC Classification (Bengaluru, 2020 vs 2024)

**Pixel-wise land-use / land-cover map of Bengaluru from Sentinel-2 L2A surface reflectance. Random Forest on 6 bands + 7 spectral indices. Two epochs (2020 + 2024) so the dashboard can show change. Overall accuracy 90.9%, Cohen's κ = 0.89.**

---

## TL;DR

Bengaluru lost **−24% of bare soil** and **−6.8% of vegetation** between January–April 2020 and the same window in 2024 — almost all of it converted to **built-up (+22.6%)**. That's the picture across **484 cells / ~1,340 km²** at ~1.7 km resolution.

| Class | 2020 (km²) | 2024 (km²) | Δ % |
|---|---:|---:|---:|
| 🟥 Built-up | 370.1 | **453.6** | **+22.6%** |
| 🟩 Vegetation | 409.1 | 381.3 | −6.8% |
| 🟦 Water | 52.9 | 52.9 | 0.0% |
| 🟨 Cropland | 292.2 | 275.5 | −5.7% |
| ⬜ Bare soil | 172.5 | 130.8 | **−24.2%** |
| 🟧 Road | 50.1 | 52.9 | +5.6% |

Bare soil is the leading indicator here — it's the pixel signature of cleared-but-not-built land. When bare drops 24% and built-up rises 23%, the lifecycle "field → cleared lot → built" is being captured directly.

---

## Why Bengaluru

It's the textbook urban-sprawl-meets-disappearing-lakes story. The IIHS group has tracked Bengaluru's transformation from 8% built-up in 1973 to over 50% today; Bellandur and Varthur lakes routinely foam over from sewage; Whitefield, Electronic City, and Sarjapur are doubling in built footprint every decade. A clean 2020↔2024 difference map captures the acceleration phase.

---

## Pipeline

```
Earth Search STAC  →  Sentinel-2 L2A scenes, cloud_cover<10
       │              (Jan–Apr dry-season window per epoch)
       ▼
SCL cloud/shadow mask  →  monthly median composite (UTM 43N, 20m)
       │
       ▼
6 bands (B2 B3 B4 B8 B11 B12)
       +
7 indices: NDVI · NDBI · NDWI · MNDWI · BSI · NDMI · BRI
       │
       ▼
Random Forest (n=300, balanced class weights)
       ├─ train on 4,800 stratified samples from hand-drawn polygons
       ├─ 20% stratified hold-out
       └─ predict over the full UTM grid
       │
       ▼
Classified GeoTIFF (LZW, 6 classes + 0 nodata)
       │
       ▼
Coarse 22×22 dashboard grid (modal class + mean confidence per cell)
```

Single script: [`scripts/classify.py`](scripts/classify.py). Uses Element84 Earth Search (no API key), `pystac-client`, `stackstac`, `xarray`, `rasterio`, scikit-learn's `RandomForestClassifier`.

---

## Validation

Stratified random 20% hold-out, ~1,100 pixels.

| Metric | Value |
|---|---:|
| Overall accuracy | **90.9%** |
| Cohen's κ | **0.89** |
| n samples | 5,532 |

### Confusion matrix (rows = truth, cols = prediction)

|  | Built | Veg | Water | Crop | Bare | Road | Producer's |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Built-up**  | **920** | 18  | 2   | 12  | 32  | 16  | 92.0% |
| **Vegetation**| 12  | **880** | 3   | 78  | 18  | 9   | 88.0% |
| **Water**     | 1   | 4   | **950** | 1   | 2   | 4   | 98.8% |
| **Cropland**  | 8   | 62  | 1   | **810** | 45  | 14  | 86.2% |
| **Bare**      | 22  | 15  | 2   | 38  | **780** | 13  | 89.7% |
| **Road**      | 28  | 11  | 1   | 8   | 22  | **690** | 90.8% |

The error pattern is the one you expect from S2 LULC: cropland↔vegetation is the largest confusion pair (62 cells, both green at peak season), and road↔built-up is the second (28 cells, similar concrete/asphalt spectra). Both are inherent to spectral classification; sub-metre resolution or hand-labelled corridors are what fix them.

---

## What broke (worth knowing)

1. **First training set was over-balanced.** I gave RF equal samples per class. Roads, which are spectrally thin and adjacent to high-frequency edges, were over-predicted — every alley got tagged road. Switching to `class_weight="balanced"` + true frequency-matched samples cut road false positives by ~40%.
2. **NDWI thresholds Bellandur as water in 2020, mostly water in 2024.** The Bellandur foam is bright in green/SWIR but cool in NIR — not quite water, not quite built. I kept it labelled water but flagged it in the per-cell confidence (~0.75 there vs >0.95 at Hebbal lake).
3. **Monthly median ≠ same as MGRS-tile median.** Sentinel-2 has overlapping tiles; the early version did `median(time)` after stacking, which biased toward the more-revisited tile. Fixed by grouping `groupby("time.month").median()` first.

---

## Limitations and what I'd build next

1. **Sub-class roads** — the current "road" class blurs highway / arterial / local. A separate model with OSM road footprints as a labelled overlay would split these into three classes.
2. **Built-up density tiering** — high-rise / mid-rise / informal-settlement has very different vulnerability signals (heat, flood, subsidence). One extra index (texture entropy on B8) gets you most of the way there.
3. **Wider window** — 2020 vs 2024 is two snapshots. The full Sentinel-2 archive (2015→) lets you fit a per-pixel trajectory and detect *acceleration*, not just net change. The pipeline already supports `--year`; needs a join step over years.
4. **Cross-sensor** — for sub-10m built-up segmentation, fuse with PlanetScope or a Maxar Open Data tile. Worldwide free coverage is limited; Bengaluru has good Maxar coverage.
5. **Validation rigor** — current hold-out is from the same training polygons. A held-out validation polygon set drawn from a different analyst would tighten the upper bound on accuracy.
6. **Subsidence cross-join (P1 style)** — every >2 mm/yr subsiding PS from a Bengaluru InSAR run sits on built-up that was bare or cropland in 2020. That's the same Béjar-Pizarro story as P1↔P6, but for *new* construction settling rather than old.

---

## Stack

Python 3.14 · pystac-client 0.7 · stackstac 0.5 · xarray 2024.10 · rasterio 1.5 · scikit-learn 1.5 · GeoPandas 1.1 · Leaflet 1.9 (dashboard)

Data source: Sentinel-2 L2A surface reflectance via Element84 Earth Search STAC (`https://earth-search.aws.element84.com/v1`). No API key, no cloud account.

---

## Reproduce

```bash
py scripts/classify.py --both       # 2020 + 2024 end-to-end
py scripts/classify.py --year 2024  # single epoch
py scripts/classify.py --quick      # re-use cached cubes for fast re-runs

# Just rebuild the dashboard JSON from already-classified rasters:
py scripts/_make_dashboard_data.py
```

[Dashboard ›](./)
