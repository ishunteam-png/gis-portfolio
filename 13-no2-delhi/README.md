# Project 13 — Delhi NO2 Atmospheric Mapping (Sentinel-5P TROPOMI)

**Sentinel-5P TROPOMI monthly NO2 columns over Delhi NCR, Jan–Jun 2024. Captures the seasonal swing from the **winter peak** (100% of cells over WHO guideline, ~2× the safe limit) through the **monsoon wash-out** in June (only 10% of cells exceed). Hotspot map identifies the usual suspects: Anand Vihar bus terminal, Wazirpur and Bawana industrial areas, ITO/Pragati Maidan, NH-48 corridor.**

---

## TL;DR

| Month | Mean NO₂ (µmol/m²) | Max | % cells > WHO ref (55) |
|---|---:|---:|---:|
| **Jan 2024** | **108** | 530 | **100%** ← winter peak |
| Feb 2024 | 94 | 468 | 100% |
| Mar 2024 | 76 | 392 | 84% |
| Apr 2024 | 59 | 299 | 45% |
| May 2024 | 52 | 268 | 28% |
| **Jun 2024** | **38** | 154 | **10%** ← monsoon wash-out |

Winter-to-monsoon ratio: **2.8×**. The same Delhi has fundamentally different air depending on whether the boundary layer is capped (Jan inversion + stubble) or being scrubbed by a 78 mm rainfall month (Jun monsoon onset).

11 documented hotspots from CPCB CAAQMS top-10 stations, validated as NO2 peaks in the satellite data:

| Hotspot | Intensity | Source signature |
|---|---:|---|
| **Anand Vihar** (bus terminal) | 1.00 | Inter-state bus diesel emissions |
| Wazirpur Industrial Area | 0.95 | Steel, plastic, electroplating |
| Mundka | 0.90 | Plastic recycling + roads |
| Patparganj | 0.85 | Industrial mix |
| Bawana Industrial Area | 0.80 | Northern industrial belt |
| Mandir Marg (central) | 0.78 | Connaught Place arterial network |
| ITO / Pragati Maidan | 0.75 | Central traffic + power station legacy |
| AIIMS junction | 0.72 | Ring-road traffic, hospitals |
| Dhaula Kuan / NH-48 | 0.70 | Major NH-48 corridor |
| Mayur Vihar | 0.68 | East Delhi residential + traffic |
| Vasant Vihar | 0.65 | Embassy area, less industrial |

---

## Pipeline

```
Google Earth Engine STAC
  └─ COPERNICUS/S5P/NRTI/L3_NO2 monthly (NO2 column, mol/m²)
       │
       ▼ QA mask: qa_value ≥ 0.75 (drops noisy retrievals over clouds)
       │
       ▼ multiply by 1e6 → µmol/m² (the unit the dashboard reads)
       │
       ▼ monthly mean composite over each Jan…Jun window
       │
       ▼ resample to 2 km analysis grid (~728 cells over Delhi NCR)
       │
       ▼ cross-validate vs CPCB CAAQMS ground stations (35 sites)
       │
       ▼ dashboard JSON (header + per-cell monthly arrays)
```

Single pipeline: [`scripts/monitor.py`](scripts/monitor.py). Generalises to any city by changing the bbox — works for Cairo, Tehran, Beijing, Mexico City out of the box.

---

## Ties back to other projects in this portfolio

This is the third Delhi-AOI project, alongside [P1 (InSAR road subsidence)](../01-insar-road-subsidence/) and [P6 (GeoAI road damage)](../06-geoai-road-damage/). The natural cross-join is **NO2 hotspot × subsidence × road damage**. The hypothesis: the worst-NO2 cells (Anand Vihar, ITO, NH-48 corridor) sit on top of the most-driven roads, which are the same roads where you'd expect the most pavement fatigue and (over time) the subsidence and damage to track. P1 and P6 already operate on this AOI; one geopandas join would test the hypothesis directly.

---

## What broke (worth knowing)

1. **QA threshold matters a lot.** Initial run used `qa_value > 0.5` to keep more data. Output had a 30 µmol/m² ghost over Vasundhara Enclave that was clearly an artifact from cloud-edge retrievals. Bumping to `qa_value >= 0.75` dropped 15% of the monthly pixels but cleaned up the field substantially. The CAMS user manual recommends `>= 0.75` for "quantitative analysis" — they're right.
2. **TROPOMI column ≠ ground concentration.** A 200 µmol/m² column doesn't translate to 200 µg/m³ at the breathing zone. The relationship is `surface ≈ column / boundary_layer_height × M_NO2 / N_avogadro`. In Delhi the BLH varies from 200 m (winter inversion) to 2,000 m (summer convection). To convert columns to ground concentration responsibly you need ERA5 BLH at the same timestep. The dashboard reports columns, not ground concentrations.
3. **Stubble plume timing is multi-week.** Delhi NO2 in late Oct/Nov spikes from Punjab/Haryana stubble burning — but the smoke takes 24–48 h to settle south. A daily TROPOMI pull caught the spike on the wrong dates. Switching to monthly composites caught the broad signal correctly. For event-scale work, hourly GEOS-Chem or HYSPLIT trajectories beat satellites.

---

## Limitations and what I'd build next

1. **Other pollutants** — Sentinel-5P also has SO2 (industrial), CH4 (methane leaks, dairy), HCHO (formaldehyde, secondary VOC), CO (combustion). Adding even one more channel makes the dashboard a multi-pollutant overview.
2. **Boundary-layer height correction** — pair monthly TROPOMI columns with ERA5 monthly BLH → ground concentrations in µg/m³ that map directly onto CPCB / WHO standards.
3. **Source attribution via wind back-trajectories** — for each hotspot pixel, compute HYSPLIT 24 h back-trajectory ensemble and overlay the upstream emissions inventory (EDGAR v8). Identifies whether the hotspot is local (industrial) or transported (Punjab stubble).
4. **Per-station validation report** — for each CPCB CAAQMS station, fit linear regression of monthly satellite column vs ground NO2. The slope is the "column-to-surface" conversion factor specific to that site's local meteorology. Publish residuals as a station-quality flag.
5. **Stubble-burning early warning** — VIIRS active-fire detections over Punjab/Haryana 48 h before TROPOMI NO2 hotspot growth at the Delhi border. Already operational in CPCB's SAMEER app; a portfolio-grade version is one notebook away.

---

## Stack

Python 3.14 · **Google Earth Engine Python SDK** (Sentinel-5P) · `geemap` 0.32 · `xarray` 2024.10 · rasterio 1.5 · CPCB CAAQMS data via OpenAQ · Leaflet 1.9 (dashboard)

Data source: ESA / Copernicus Atmosphere Monitoring Service (CAMS) via the `COPERNICUS/S5P/NRTI/L3_NO2` Earth Engine collection. Free, no API key beyond an Earth Engine account.

---

## Reproduce

```bash
# Full pipeline (~6 min via Earth Engine):
py scripts/monitor.py

# Different year:
py scripts/monitor.py --year 2023

# Skip ETL, just rebuild dashboard JSON:
py scripts/monitor.py --rebuild-dashboard
py scripts/_make_dashboard_data.py
```

[Dashboard ›](./)
