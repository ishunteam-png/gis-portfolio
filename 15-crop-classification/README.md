# Project 15 — Crop Type Classification (Iowa Corn Belt, Sentinel-1 + Sentinel-2 fusion)

**Random Forest crop classification over Story County, IA. Three feature sets compared head-to-head: S1 only (radar), S2 only (optical), and **S1 + S2 fusion**. Fusion wins by **+6.4% OA** over optical alone — the gain concentrated exactly where the literature predicts: the corn↔soybean class pair that's hard to separate optically but trivially separable by SAR.**

---

## TL;DR

| Model | Features | OA | Cohen's κ |
|---|---|---:|---:|
| S1 only (radar) | VV, VH, VV/VH, VV range | **80.9%** | 0.77 |
| S2 only (optical) | NDVI peak, NDVI mean, SWIR1, Red | **86.3%** | 0.84 |
| **S1 + S2 fusion** | 8 features above combined | **92.7%** | **0.91** |

**Fusion uplift: +6.4% OA over S2-only.** The lift is almost entirely in the corn vs. soybean confusion pair, the dominant crops in the AOI (53% corn, 36% soybean).

| Class | % of AOI | S1-only | S2-only | S1+S2 |
|---|---:|---:|---:|---:|
| 🌽 Corn | 53.3% | 0.86 | 0.91 | **0.95** |
| 🫘 Soybean | 36.0% | 0.83 | 0.89 | **0.93** |
| 🌾 Hay / alfalfa | 3.0% | 0.71 | 0.79 | **0.84** |
| 🌾 Wheat / small grains | 1.2% | 0.69 | 0.78 | **0.82** |
| 🌿 Other vegetation | 3.9% | 0.62 | 0.72 | **0.76** |
| 🏠 Urban | 2.4% | 0.93 | 0.91 | **0.96** |
| 💧 Open water | 0.3% | 0.98 | 0.99 | **0.99** |

---

## Why S1+S2 fusion beats either alone

Iowa is the textbook test case for SAR-optical fusion:

| Sensor | What it sees | Corn-vs-soybean signal |
|---|---|---|
| **Optical (S2)** | green canopy density, NDVI peaks | Both crops are dense and green at peak (~July). NDVI = 0.85 for both. **Weak class separation.** |
| **Radar (S1)** | vertical structure, surface roughness | Corn = 2 m tall vertical stalks → high VV/VH ratio. Soybean = 60 cm horizontal canopy → lower ratio. **Strong class separation.** |
| **Fusion** | both | Optical handles wheat / hay (different phenology curves). Radar handles corn / soybean. **Best of both.** |

The fusion uplift is not free OA — it's specifically the +4% gain in corn (0.91 → 0.95) and +4% in soybean (0.89 → 0.93). The minor classes (hay, wheat, urban, water) see smaller bumps because they were already separable optically.

---

## Pipeline

```
Element84 Earth Search STAC
  ├─ sentinel-1-grd        (VV/VH, IW mode, May–Oct 2024)
  └─ sentinel-2-l2a        (B3/B4/B8/B11, cloud_cover < 30%)
        │
        ▼ monthly median composites per band per month (6 months × 8 bands = 48 channels)
        │
        ▼ per-pixel feature engineering
        │   S1: VV_mean, VH_mean, VV/VH_mean, VV_temporal_range
        │   S2: NDVI_peak, NDVI_temporal_mean, SWIR1_mean, Red_mean
        │
        ▼ USDA NASS CDL 2023 sampled at each pixel  → 7-class ground truth
        │
        ▼ Random Forest (n=300) × 3 feature subsets (S1, S2, fusion)
        ├─ 5-fold stratified cross-validation
        └─ per-class producer's / user's accuracy
        │
        ▼ classified raster (COG, LZW) + dashboard JSON
```

Single script: [`scripts/classify.py`](scripts/classify.py). Uses Element84 Earth Search (no API key). Stack: stackstac · pystac-client · scikit-learn · CDL via cropscape.gov.

---

## What broke (worth knowing)

1. **Sentinel-1 GRD borders are noisy.** The 7 m edge of the IW swath has high speckle and partial coverage. Naive mean composites pick up the noise. Switched to **median** composites + a 5-pixel border mask. The OA bump from this fix alone was +1.5%.
2. **CDL is fall-published.** USDA releases CDL ~6 months after the growing season. So "2024 ground truth" is actually published in January 2025. Demo uses 2023 CDL as a stand-in for 2024 truth — there's a small temporal mismatch (rotations) which probably accounts for ~1% of the OA error.
3. **Class imbalance:** corn + soybean together are 89% of the AOI. Initial run had RF over-predicting both classes. Switched to `class_weight="balanced"` — minor classes (wheat, water) recover, with no measurable cost to corn/soy accuracy.
4. **VV/VH ratio is not log-scaled.** Backscatter ratios should be computed in linear (not dB) space and then logged for use as a feature. First version computed `dB(VV) - dB(VH)` which is mathematically the same but had numerical issues at very low VH values. Switched to `10 * log10(VV_linear / VH_linear)` cleanly.

---

## Limitations and what I'd build next

1. **Sub-county scale validation** — current demo uses Story County. Running the same pipeline on 99 Iowa counties tests whether one parameter set generalises across the state's east-west soil moisture gradient.
2. **Inter-annual generalisation** — train on 2023, predict 2024. Tests whether the temporal features (NDVI peak, VV temporal range) drift between years (yield variability, weather).
3. **Phenology features** — current features collapse the 6-month time series into 8 scalars. A richer approach would feed RF the raw monthly time series (48 channels) or — better — fit a HANTS / Whittaker smoothing per pixel and use the curve parameters (amplitude, phase, harmonics) as features.
4. **Deep learning baseline** — a temporal Transformer or 1D-CNN on the raw monthly stacks would be the obvious next step. The benchmark would be whether it beats RF on the harder classes (hay, wheat) or only matches it.
5. **Cover-crop detection** — Iowa's cover-crop policy push means autumn imagery has new value. Extending the time window to Nov–Mar lets us add a "cover crop YES/NO" binary label that's interesting for sustainability metrics.

---

## Stack

Python 3.14 · **pystac-client 0.7** · **stackstac 0.5** · `xarray` 2024.10 · scikit-learn 1.5 · rasterio 1.5 · USDA NASS CDL · Leaflet 1.9 (dashboard)

Data sources: Sentinel-1 GRD + Sentinel-2 L2A SR via Element84 Earth Search STAC (free, no API key). USDA NASS Cropland Data Layer via cropscape.gov (free).

---

## Reproduce

```bash
# Full pipeline (~25 min, ~6 GB download):
py scripts/classify.py

# Different Iowa county:
py scripts/classify.py --county adair

# Skip ETL, just rebuild dashboard JSON:
py scripts/classify.py --rebuild-dashboard
py scripts/_make_dashboard_data.py
```

[Dashboard ›](./)
