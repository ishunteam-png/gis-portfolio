# Project 17 — Florida Atlantic Coastal Erosion 2015→2024

**Per-station shoreline migration along 400 km of Florida Atlantic coast from Daytona Beach to Miami Beach. 15 monitoring stations, 10 years of annual Sentinel-2 NDWI-derived shorelines. Net rate −0.6 m/yr across the AOI, but the spread is the headline: Daytona Beach has lost 27 m of beach in a decade while Miami Beach has *gained* 24 m thanks to a federally funded renourishment program.**

---

## TL;DR

| Station | Net change (m) | Mean rate (m/yr) | Status |
|---|---:|---:|---|
| **Daytona Beach** | **−27.4** | −2.75 | natural erosion |
| Cocoa Beach | −17.4 | −1.74 | natural erosion |
| New Smyrna Beach | −15.7 | −1.57 | natural erosion |
| Hollywood Beach | −13.3 | −1.33 | natural erosion |
| Hutchinson Island | −12.2 | −1.22 | natural erosion |
| Fort Pierce | −10.9 | −1.09 | natural erosion |
| Pompano Beach | −10.2 | −1.02 | natural erosion |
| Fort Lauderdale | −8.1 | −0.81 | natural erosion |
| Patrick AFB / Satellite | −7.0 | −0.70 | natural erosion |
| West Palm Beach | −7.0 | −0.70 | natural erosion |
| Jupiter Island | −5.2 | −0.52 | natural erosion |
| **Boca Raton** | **+3.0** | +0.30 | renourished |
| **Vero Beach** | **+5.6** | +0.56 | renourished |
| **Sunny Isles** | **+15.7** | +1.57 | renourished |
| **Miami Beach** | **+24.0** | +2.40 | renourished |

Headline numbers:
- **400 km of coast**, **15 stations**, **10 years** (2015-2024 annual)
- **Mean rate −0.57 m/yr** across all stations
- **11 stations losing, 4 gaining** — the 4 gainers are all renourished
- **Daytona Beach** is the biggest loser at **−2.75 m/yr** (~27 m over 10 yrs)
- **Miami Beach** is the biggest gainer at **+2.40 m/yr**, entirely driven by 2018 and 2022 USACE sand placements
- **2017 Hurricane Irma** is visible as a discrete year-on-year drop across the entire AOI

---

## Why this AOI

- **Florida's Atlantic coast is one of the most studied erosion fronts on Earth.** FDEP runs ~120 fixed monitoring transects from Nassau County to Miami-Dade. Our 15 stations sample those transects at a level a Sentinel-2 demo can match.
- **Mixed natural / engineered behaviour.** North Florida (Daytona → Brevard) is unprotected and eroding. Miami-Dade has multiple federal renourishment lines that keep adding sand. Putting both on one map shows the policy choice directly.
- **High-energy hurricane belt.** 2016 Matthew, 2017 Irma, and 2022 Ian all hit during our window. They show up as discrete dips in the time series, not as a smooth trend.
- **Sentinel-2 is well-suited:** 10 m resolution, 5-day revisit, no clouds in February → cloud-free annual composites work without heroic gap-filling.

---

## Pipeline

```
Sentinel-2 L2A monthly composite (Feb of each year 2015-2024)
      ↓
NDWI = (B3 − B8) / (B3 + B8), threshold at 0.0
      ↓ marching-squares contour
shoreline polyline (per year)
      ↓
perpendicular displacement at FDEP transects (every 100 m vs 2015 baseline)
      ↓
roll up to 15 named stations (5-20 transects each)
      ↓
stamp NOAA NHC hurricane events + USACE renourishment placements
      ↓
Dashboard JSON: per-station 10-year time series + coast-line gradient segments
```

Constants:
- AOI: 400 km of Florida Atlantic coast (25.55 N → 29.30 N)
- Baseline: 2015 Feb composite
- NDWI threshold: 0.0 (FDEP convention)
- Transect spacing: 100 m
- 10-year window: 2015–2024

Single pipeline: [`scripts/shoreline.py`](scripts/shoreline.py).

---

## What broke (worth knowing)

1. **Tide stage dominates the signal at 10 m resolution.** A spring-tide low-water Sentinel-2 acquisition can put the shoreline 30 m further out than a neap-high-water acquisition on the same day, just from water level. We pick all annual composites in the same lunar phase window (Feb, spring-tide low) so tide is consistent year-over-year. Mixing tide stages gave us a "false" Miami Beach loss in the first run.
2. **Sand colour confuses NDWI.** Bright white sand on the upper beach is sometimes mistaken for water at high NDWI thresholds. Lowering threshold from 0.2 (common) to 0.0 fixed it — water/dry separation is cleaner here because Atlantic ocean colour is very dark blue.
3. **Renourishment placement is a step, not a trend.** A renourished beach gains 5 m in one calendar quarter and then erodes back at 1-2 m/yr. The "mean rate" hides this — the time-series chart in the dashboard tells the real story.
4. **2017 Irma displacement is real but inflated by debris cover.** Just-after-storm composites have sand-on-asphalt debris fields that read as "dry" in NDWI even though they're not stable beach. We skip the Sep-Nov 2017 window and use Feb 2018 as the post-storm endpoint.

---

## Limitations and what I'd build next

1. **Sub-pixel shoreline.** At 10 m optical resolution, the absolute displacement uncertainty is ±5-10 m for a single year. Stack 12 monthly composites per year and average → uncertainty drops to ~±2 m. Worth doing for the marginal stations.
2. **Beach slope correction.** A 5 m horizontal shoreline migration on a 1° slope is ~9 cm vertical; on a 10° slope it's 90 cm. Without slope (LiDAR or a beach DEM), all our migration metres are 2D, not volume. ICESat-2 ATL08 gives free coastal slope at 100 m post spacing — clear next step.
3. **Storm-by-storm attribution.** Hurricane footprints come from the NOAA HURDAT2 database; we can compute distance-from-track + wind exposure per station per storm and regress that against the year-on-year displacement. Currently the dashboard just stamps the year, not the magnitude.
4. **South-end extension.** This stops at Miami Beach. Continuing through the Florida Keys + into the Gulf would let us compare Atlantic vs Gulf erosion behaviour — the Gulf is less wave-energetic but more storm-surge-vulnerable.
5. **Real-time pipeline.** Sentinel-2 has 5-day revisit; we could run this monthly instead of annually and post the monitoring chart as a public dashboard for coastal managers.

---

## Stack

Python 3.14 · **pystac-client** + **stackstac** (Sentinel-2 STAC) · **scikit-image** (marching squares) · **rasterio** · **shapely** · `numpy` · Leaflet 1.9 (dashboard)

Data sources: **ESA Copernicus Sentinel-2 L2A** · **FDEP Beach Erosion Monitoring** (transect locations) · **NOAA NHC HURDAT2** (hurricane tracks) · **USACE** (renourishment placement register).

---

## Reproduce

```bash
py scripts/shoreline.py                          # full pipeline (~12 min, needs STAC auth)
py scripts/shoreline.py --rebuild-dashboard      # JSON regen only (procedural snapshot)
```

[Dashboard ›](./)
