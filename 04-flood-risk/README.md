# Project 4 — Jakarta Compound Flood Risk (Multi-Factor)

**Build a per-pixel flood-risk index for the world's most flood-prone megacity by combining FOUR independent terrain-and-land-use signals from open data, then quantify the exposure of every hospital, school, fire station and police station in the AOI.**

![Jakarta — composite flood-risk model (4 panels: risk band, HAND, imperviousness, drainage density)](assets/flood_hero.png)

---

## Why Jakarta

Jakarta is the canonical case study in urban flood hazard:

- **40 %** of the city sits below sea level
- North Jakarta subsides at **10–25 cm/yr** (one of the fastest rates in the world)
- **13 rivers** cross the city before discharging into the Java Sea
- Monsoon rainfall and tidal pulses interact to produce **compound floods** that simple fluvial-only models can't capture
- The situation is so severe that **Indonesia is relocating its capital** from Jakarta to a new city (Nusantara) on Borneo, ~1,300 km away

If your flood model works in Jakarta, it works anywhere.

---

## TL;DR

For a 23 km × 26 km bbox covering central Jakarta, the model produces a composite 0–1 flood-risk index for **1.7 million pixels** at ~20 m resolution, then bands each pixel into low / moderate / high / very high. The four input signals:

| Signal | Direction | Weight |
|---|---|---:|
| **HAND** (Height Above Nearest Drainage) | low value = high risk | 0.40 |
| **Slope** (degrees, from DEM gradient) | low value = high risk | 0.25 |
| **Imperviousness** (impervious LU / total LU within 500 m) | high value = high risk | 0.20 |
| **Drainage density** (m of waterway per km², 500 m disk) | high value = LOW risk | 0.15 |

### Headline numbers

- **DEM:** Mapzen Terrain Tiles, zoom 12, ~20 m resolution, elevation **−55 to +92 m** (yes — negative; coastal North Jakarta is below sea level)
- **Waterways:** 1,078 OSM features
- **Land use:** 1,603 impervious + 5,517 pervious LU polygons
- **Critical infrastructure analysed:** **7,371 assets**
- **Wall-clock pipeline:** ~10 min end-to-end

### Critical-infrastructure exposure to high + very-high risk

![Critical infrastructure exposure chart](assets/critical_infra_chart.png)

| Asset type | High + Very High count |
|---|---:|
| Schools | **1,360** |
| Kindergartens | **725** |
| Clinics | **627** |
| Hospitals | **138** |
| Police stations | **105** |
| Universities + colleges | **128** |
| Fire stations | **45** |
| Ambulance stations | **22** |

**This is the headline a city emergency-management agency actually wants.**

---

## Why a 4-signal model instead of just HAND

A pure-HAND model gives the *fluvial baseline*. In a flat coastal delta city like Jakarta you also need:

- **Slope** for *ponding* — flat parking lots accumulate water independent of distance to river
- **Imperviousness** for *runoff generation* — sealed surfaces convert 90 % of rain to runoff
- **Drainage density** for *evacuation capacity* — sparse-drain kampungs pond longer than planned grids

This captures the compound nature of Jakarta floods that a single-signal model misses.

---

## Stack

rasterio 1.5 · scipy.ndimage (distance_transform_edt + convolve) · GeoPandas · OSMnx · Folium

Single script: [`scripts/flood.py`](scripts/flood.py) (~360 lines).

---

## Limitations and what I'd build next

1. Buildings footprint pull is incomplete — use Microsoft Building Footprints (28 M Indonesia buildings) instead of OSM.
2. HAND uses Euclidean nearest — D8 flow routing would fix negative-HAND artefacts.
3. No tidal / coastal flooding — add storm-surge layer (GTSM model output).
4. No subsidence layer — add Sentinel-1 PSI a la Project 1 for Jakarta and re-baseline annually.
5. No rainfall scenarios — couple with SCS-CN runoff and ESA WorldCover land cover.
6. Population, not just buildings — join WorldPop / HRSL for "X people exposed in band Y".
7. Validation against Jakarta's 2007/2013/2020 flood extent maps — Critical Success Index.
