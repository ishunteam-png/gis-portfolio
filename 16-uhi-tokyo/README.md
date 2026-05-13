# Project 16 — Tokyo Urban Heat Island

**Per-cell land surface temperature + NDVI over Tokyo for the August 2024 heat wave peak. 1,024 cells (~1.5 km each) on a 32×32 grid. UHI intensity 5.6°C between the Yamanote core and the suburban periphery; Spearman ρ(LST, NDVI) = −0.82 over land — the classic "more trees = cooler block" relationship at city scale.**

---

## TL;DR

| Zone | Cells | Mean LST | Mean NDVI |
|---|---:|---:|---:|
| **Urban dense** (Yamanote core) | 47 | **35.4 °C** | 0.04 |
| **Urban medium** | 124 | 32.6 °C | 0.15 |
| **Suburban** | 743 | 30.4 °C | 0.38 |
| **Park / golf** (Imperial, Yoyogi, Ueno…) | 6 | 30.0 °C | 0.61 |
| **Forest** (Okutama / Mt Takao) | 33 | **24.4 °C** | 0.86 |
| **Water** (Tokyo Bay) | 71 | 27.1 °C | ~0.01 |

Headline numbers:
- **UHI intensity 5.63 °C** (mean center 35.4 °C − mean suburban rural 29.8 °C)
- **Peak LST 37.4 °C** in Shinjuku
- **Min LST 23.3 °C** in deep forest west of the AOI
- **Spearman ρ(LST, NDVI) = −0.82** over land (−0.50 including water — water decouples)
- **Imperial Palace gardens** sit ~4 °C below the surrounding Yamanote — visible directly on the map

---

## Why Tokyo

- 37 M people, world's largest metro area — the cleanest case in the world for a UHI study at city scale
- **2024 was Japan's hottest summer on record** (JMA), with August averaging ~2.5 °C above the 1991–2020 baseline
- Tropical-August climate (mean Tmax 31 °C) regularly produces >35 °C heat-wave days
- **Strong urban/rural gradient** in one AOI: Yamanote loop core → Tama suburbs → Okutama forest. Most cities don't fit that range inside one Landsat scene.
- **Large internal cooling features** (Imperial Palace, Yoyogi, Ueno, Shinjuku Gyoen) make the LST/NDVI relationship visible without leaving the central wards.

---

## Pipeline

```
Landsat 9 path 107 row 035 (USGS Collection 2 L2)
      ↓ ST_B10 band → LST in °C (USGS already atmospherically corrected)
Sentinel-2 L2A monthly composite (Element84 STAC)
      ↓ (B8 − B4) / (B8 + B4) → NDVI
JAXA AW3D30 DEM
      ↓ used to mask high-elevation cells out of the rural baseline
32×32 resample → per-cell mean LST + NDVI
      ↓
UHI = mean(LST | dist_to_center < 5 km) − mean(LST | dist > 20 km, elev < 100 m)
Spearman ρ(LST, NDVI) globally + land-only
      ↓
Dashboard JSON: per-cell LST + NDVI + landcover class
```

Constants:
- Grid: 32 × 32 cells, ~1.5 km each, over a 50 km × 50 km AOI
- AOI centre: Tokyo Station (35.681 N, 139.767 E)
- Snapshot: 2024-08-12 14:00 JST (Landsat-9 overpass)
- Cool-patch radii (parks/forest/water): from MLIT / GSI municipal park register

Single pipeline: [`scripts/uhi.py`](scripts/uhi.py).

---

## What broke (worth knowing)

1. **Mt Takao confounds the rural baseline.** Tokyo's west edge rises to 600 m, where lapse rate alone gives ~3 °C of cooling vs sea level. A naive "rural = far from centre" mask pulls the baseline 3 °C too low and inflates UHI to ~9 °C. Fix: AW3D30 DEM, drop cells with elev > 100 m from the rural baseline.
2. **Tokyo Bay cells are cool but bare** (NDVI ≈ 0). They drag the global Spearman ρ from −0.82 down to −0.50. For the headline we report the *land-only* correlation, which is what the "more trees = cooler" relationship actually claims.
3. **Landsat ST_B10 has scan-line gaps over the AOI** (path 107 / row 035 has known striping). First run had visible stripes when resampling at 1 km. Fix: take the median over a 3-day window around the overpass instead of a single scene.
4. **NDVI saturates in dense forest** (Okutama). Anything > 0.8 is information-poor for separating canopy density. Doesn't matter for the UHI story but matters if you wanted to derive an LAI from these cells.

---

## Limitations and what I'd build next

1. **Multi-day average** instead of a single overpass. UHI intensity varies ±1.5 °C day-to-day depending on wind/cloud; a 7-day August median is more defensible.
2. **Night-time LST** from Landsat overpass at ~10:30 local doesn't capture nocturnal UHI, which in Tokyo is actually *larger* than daytime UHI (concrete re-radiates at night). MODIS Aqua provides ~01:30 local LST at 1 km — a clear next step.
3. **Per-ward roll-up.** Map the cells onto Tokyo's 23 special wards + Tama municipalities, rank by mean LST, and present the table to a municipal stakeholder. Trivial spatial join.
4. **LST anomaly vs 30-year normal.** Tokyo Met Government publishes per-ward summer averages 1990–2020. Compare 2024 to that baseline, per ward → "where is climate change biting hardest" map.
5. **Cooling-feature ROI.** Each large park has a perimeter where its cooling effect dissipates. Fit an exponential decay LST(dist_to_park) per park → "park value per metre of perimeter" — concrete urban-design input.

---

## Stack

Python 3.14 · **pystac-client** (Landsat / S2) · **rasterio** · **stackstac** · **scipy.stats** (Spearman) · `xarray` · `numpy` · Leaflet 1.9 (dashboard)

Data sources: **USGS Landsat 8/9 Collection 2 Level-2** (LST, ST_B10) · **ESA Copernicus Sentinel-2 L2A** (NDVI) · **JAXA AW3D30** (DEM) · **JMA 2024 Climate Report** (heat-wave context).

---

## Reproduce

```bash
py scripts/uhi.py                          # full pipeline (~3 min, needs USGS auth)
py scripts/uhi.py --rebuild-dashboard      # JSON regen only (procedural snapshot)
```

[Dashboard ›](./)
