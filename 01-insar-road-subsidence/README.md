# Project 1 — InSAR Road Subsidence Monitoring (Delhi)

**Strict EGMS-L3 Sentinel-1 InSAR pilot · 3-year window · 2,555 Persistent Scatterers · true 2D vertical + east-west decomposition**

![Headline — vertical + east-west velocity over Najafgarh Road, Delhi](assets/01_velocity_dual_panel.png)

---

## TL;DR

I built an end-to-end Sentinel-1 InSAR pipeline that measures **millimetre-per-year ground motion** of a 4 km × 4.5 km section of Najafgarh Road in southwest Delhi, using **3 years of free satellite data** (May 2023 → April 2026). The pipeline is methodologically equivalent to the **European Ground Motion Service (EGMS-L3)** — the European reference for terrestrial subsidence monitoring — and resolves motion into separate vertical and east-west components, anchored to the ITRF14 reference frame.

**Headline numbers**
- **2,555 Persistent Scatterers** passing the strict EGMS-PSI gate (spatial coherence ≥ 0.70 in both ascending and descending stacks)
- **Vertical velocity:** −10.32 to +4.67 mm/yr · mean −1.20 mm/yr (gentle subsidence)
- **East-west velocity:** −7.83 to +8.42 mm/yr · mean +1.01 mm/yr (near-zero, expected for rigid-plate road infra)
- **Geometric diversity** (|det| of the 2×2 LOS-to-ENU system): **0.95** — excellent
- **Wall-clock cost:** ~5.5 hours processing time, ~$1 in AWS compute, $0 in data licensing

---

## The problem

Road and infrastructure operators in India and Southeast Asia need to know **which sections of road are settling, by how much, and how fast** — before the surface cracks, before bridges shift, before sewer pipes break. The gold-standard answer comes from levelling surveys (expensive, slow, point-only) or commercial InSAR services (€20k+ per AOI).

This project demonstrates that the **same answer** — at EGMS quality — can be produced from free Sentinel-1 SAR data using open-source tooling, for a tiny fraction of the cost.

---

## Why InSAR, and why "EGMS-L3"

**InSAR** (Interferometric Synthetic Aperture Radar) measures the phase difference between two satellite SAR passes over the same point. Because Sentinel-1 has a 5.6 cm wavelength, that phase difference resolves displacement at **single-millimetre** precision — but only along the line-of-sight (LOS) of the satellite.

**EGMS-L3** is the most demanding tier of the European Ground Motion Service product family. It requires:

1. **Dual-track coverage** — ascending *and* descending passes over the same AOI.
2. **True 2D decomposition** — combining ASC and DSC line-of-sight velocities into separate **vertical** and **east-west** components, so subsidence is no longer confused with horizontal motion.
3. **Atmospheric correction** — removing tropospheric phase delay (ERA5 reanalysis).
4. **Absolute reference frame** — tying the relative measurements to a known global frame (ITRF14) via the local plate motion model.

Most "InSAR studies" you see online are L2-equivalent: single-track, LOS-only, no atmospheric correction. This pilot does all four L3 steps end-to-end.

---

## Results

### Vertical velocity (V_U)

![Vertical velocity map](assets/02_vertical_velocity.png)

Clear subsidence cluster in the **southwest corner** of the AOI (down to −10 mm/yr) and gentle uplift in the **upper-right** (up to +5 mm/yr) — consistent with published groundwater-extraction subsidence patterns in this district (Mishra et al. 2022, Lakhanpal et al. 2024).

### East-west velocity (V_E, plate-motion-corrected)

![East-west velocity map](assets/03_eastwest_velocity.png)

After subtracting the Indian-plate motion (~40 mm/yr eastward in ITRF14), residual east-west velocity is patchy and near-zero — the expected signature for road infrastructure on rigid crust, and a clean QA check on the decomposition.

### Decomposition QA — per-PS V_U vs V_E

![PS scatter — V_U vs V_E decomposition](assets/04_decomposition_scatter.png)

Each dot is one Persistent Scatterer. The cloud is correctly distributed with the **bulk of the spread along the vertical axis**, confirming the 2D decomposition is well-conditioned.

### Time series at the most-subsiding pixel

![Time series — ASC and DSC LOS at most-subsiding PS](assets/05_timeseries.png)

3 years of LOS displacement at the worst-subsiding PS in the AOI, plotted independently for the ASC and DSC stacks. Both tracks show **monotonic subsidence** with consistent slope — strong cross-stack agreement, no thermal seasonality.

---

## Quality indicators

| Metric | Value | Reading |
|---|---:|---|
| Persistent Scatterers (strict EGMS-PSI gate) | 2,555 | Dense urban scattering |
| Mean temporal coherence (ASC, DSC) | > 0.90 | Excellent — EGMS minimum is 0.70 |
| 2×2 LOS-to-ENU system |det| (mean) | 0.95 | Excellent geometric diversity |
| ASC / DSC LOS velocity std | 2.3 / 1.7 mm/yr | Realistic spatial variation |
| Atmospheric correction | ERA5 via PyAPS3 (165 GRIB files) | Reduces noise to EGMS floor (~2–3 mm) |

---

## Stack

| Layer | Tool |
|---|---|
| SAR data | Sentinel-1 SLC (ASF Vertex, free) |
| Pair generation | ASF HyP3 (ISCE2 backend, cloud) |
| Phase unwrapping | SNAPHU 2-D |
| Time-series inversion | MintPy SBAS WLS |
| Atmospheric correction | PyAPS3 + ERA5 reanalysis |
| Reference frame | ITRF14 NNR + Altamimi (2017) Indian-plate Euler pole |
| Decomposition | Per-pixel 2×2 LOS-to-ENU solve (V_N dropped) |
| Visualization | matplotlib, Plotly, contextily |
| Dashboard | Streamlit (4 tabs: map / decomposition / distribution / data / methodology) |
| Infra | AWS EC2 (t3.xlarge for processing, t3.micro for dashboard) |

---

## Run it yourself

The complete pipeline source — 10 numbered scripts, `00_orchestrate.py` through `09_pull_results.py` — lives in the SATALITE working repo (private). The numbered scripts run top-to-bottom on a fresh Ubuntu 22.04 EC2 instance with `conda activate insar`. A 3-year pilot at a new AOI takes **~5.5 wall-clock hours** end-to-end.

**Sample outputs in this repo:**

- [`data/summary.json`](data/summary.json) — pilot-level statistics
- The dashboard at [Project 5](../05-web-gis-dashboard/) renders the full PS dataset

---

## What I'd build next

- **Operational alerting** — schedule the pipeline to re-run weekly as new Sentinel-1 acquisitions land, with anomaly detection on per-PS velocity drift and email/Slack alerts when any PS crosses a threshold.
- **Multi-AOI orchestration** — automate AOI definition from a road network shapefile, so a city DOT can run "monitor every flyover in Delhi" as a single config file.
- **Cross-validation with GNSS** — co-locate the AOI with the nearest IGS station and compute a residual-velocity goodness-of-fit on the PMM tie.
- **PSI ↔ DS combination** — extend from PS-only to combined PS + Distributed Scatterer SqueeSAR-style inversion for better rural / vegetation coverage.

---

## References

- Altamimi, Z., Métivier, L., & Collilieux, X. (2017). *ITRF2014 plate motion model.* Geophys. J. Int.
- Mishra et al. (2022) — Groundwater-driven subsidence in NCR Delhi.
- Lakhanpal et al. (2024) — InSAR-derived land deformation in Dwarka.
- EGMS product specification — Copernicus Land Monitoring Service.
