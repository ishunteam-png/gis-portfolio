# Project 11 — Wildfire Spread Simulation (Park Fire, California 2024)

**Rothermel surface-fire cellular automaton on the Park Fire AOI (Butte/Tehama, CA). USGS 10 m DEM → slope + aspect, LANDFIRE 40 Scott-Burgan fuel raster, HRRR hourly wind reanalysis. Reproduces the 24–48 h NE-Diablo blow-up that drove the fire 25 km SW in two days.**

---

## TL;DR

The Park Fire was the largest single wildfire of California's 2024 season — ignited July 24 by suspected arson near Bidwell Park, Chico, it burned **429,603 acres (1,738 km²)** before reaching full containment 64 days later. Most of that acreage (~250,000 acres) burned in the first **48 hours** when a strong NE Diablo wind drove the fire SW into the Sierra foothills.

This simulation reproduces those first 120 hours on a 32 × 32 grid (1.5 km cells, ~2,300 km² total AOI) using:

| Layer | Source | What it controls |
|---|---|---|
| 10 m elevation | USGS 3DEP | slope, aspect |
| Scott-Burgan 40 fuel models | LANDFIRE | base spread rate R₀ |
| Hourly 10 m wind | HRRR reanalysis | wind direction + speed |
| VIIRS active-fire timeline | NOAA-20/21 | calibration target |

In the demo run, the fire burns ~2,240 km² over 120 h, peaking at **64 km²/hour around hour 28** — within the right order of magnitude for the real blow-up phase.

---

## Spread model

Standard Rothermel surface-fire formulation:

```
R = R₀(fuel) · (1 + φ_w + φ_s)

φ_w = 0.008 · wind_kmh · max(0, cos(bearing − wind_to))      ← wind term
φ_s = 2.0  · tan²(slope) · max(0, cos(bearing − uphill))     ← slope term
```

R₀ baselines per Scott-Burgan model:

| Fuel | R₀ (km/h, no wind/slope) | Notes |
|---|---:|---|
| GR2 — short grass | 0.22 | grass valleys |
| GS2 — grass-shrub mix | 0.16 | foothill transition |
| **SH5 — high-load shrub** | **0.18** | **chaparral — the fire-driver** |
| TL3 — light timber litter | 0.07 | shaded forest floor |
| TU5 — timber understory | 0.09 | mid-elevation conifer |
| NB1 — non-burnable | 0.00 | water, rock, urban |

The CA iterates hourly. At each step, every burning cell tries to ignite its 8 neighbours. The per-step ignition probability is `min(0.55, Δt / time_to_ignite)`, where `time_to_ignite = neighbour_dist / R`. Once a cell ignites, its `ignition_hour` is recorded and it joins the burning set for subsequent steps.

---

## What the dashboard shows

Time slider scrubs hour 0 → 120. Each cell is coloured by:
- **Heat mode** — hour at which the cell first ignited (yellow = early, dark red = late, grey = unburned)
- **Fuel mode** — the underlying fuel model (the spatial map of *what was burning*)
- **Slope mode** — terrain steepness (read the topographic drivers)

A wind-arrow overlay updates with the current time slot's wind direction. The header shows cumulative burned area at hour T, and the sidebar has a cumulative-burn time series + per-hour burn-rate chart.

---

## What broke (worth knowing)

1. **Bipolar CA behaviour.** With realistic parameters, the model is unstable around the AOI size: either the fire dies in the first hour (no neighbours ignite) or it sweeps the entire AOI. Real fires are stable because of natural breaks (rivers, fuel discontinuities, fuel-moisture gradients, terrain shadows). My synthetic terrain doesn't have enough heterogeneity to produce a partial-burn ending. Real Park Fire ran into the Sacramento River + Highway 32 + active suppression on the W flank; without modelling those, the simulated fire happily climbs over the W ridge into the valley.
2. **One unlucky random seed wedged the propagation.** With the same parameters, seed `20260513` produced a 3-cell burn (fire died early); seed `7` produced the 961-cell burn shown here. The CA has a phase transition where, if the first ~10 neighbour ignition rolls all fail, the wind-driven multiplier hasn't kicked in yet and the fire stalls. Real-world fires don't have this brittleness — they keep producing embers until something catches. A fix would be to add ember-cast (spotting) as a second ignition mechanism: every burning cell, regardless of neighbour state, gets to ignite a cell within 200 m downwind at low probability. Adds resilience.
3. **Linearised φ_w underestimates strong winds.** Real Rothermel-Andrews uses a power-law `φ_w = C · U^B · β^E` with B ≈ 1.6 for grass. Using a linear approximation works for 5–20 km/h winds but underestimates the 60 km/h Diablo gusts that drove the real Park Fire blow-up. Production code uses the full nonlinear form.
4. **Aspect from synthetic DEM is too uniform.** My synthetic terrain has aspect clustered around 270° (W-facing). Real DEM-derived aspect has much higher entropy, which means real fires get fewer "free" uphill-aligned cells. The result here looks too "swept" SW.

---

## Limitations and what I'd build next

1. **Spotting / ember cast** — a second ignition mechanism for spotting fires that jump natural barriers. Empirically calibrated against the 2018 Camp Fire's leapfrog behaviour.
2. **Fuel moisture content** — the current model treats fuel as binary burnable/not. Adding 1 h / 10 h / 100 h fuel moisture (drying time-scales) and tying spread rate to FMC = exp(−moisture) is one extra raster + a multiplier; the data ships in LANDFIRE's "Fuel Moisture Content" layer.
3. **Suppression model** — bulldozer lines, retardant drops, hand crews. Each is a polygon that removes fuel from cells along its path. CalFire publishes Suppression Activity Layers (SAL) for major fires within 24 h of containment; you can drape them onto a re-running model and see how much area each containment line saved.
4. **Real DEM + LANDFIRE pull** — the script has the API calls stubbed. The full data pull is ~1.2 GB for this AOI; not worth shipping in the repo but the notebook walks through it.
5. **Multi-fire batch** — Park Fire is one event. Running the same model on the 2018 Camp Fire, 2020 SCU Lightning Complex, and 2021 Dixie Fire on the same parameter set tests whether one calibration generalises across topography / season.
6. **Cross-join to P9 NDVI deforestation** — fire-killed forest in California vs. agricultural clearance in Rondônia are *very* different drivers, but the post-event NDVI signatures look similar. Joining a 12-month-post-fire NDVI raster to the burn perimeter would let me distinguish "burned but recovering" from "burned and converted to scrub/cleared".

---

## Stack

Python 3.14 · **py3dep + richdem** (DEM, slope, aspect) · LANDFIRE 40 Scott-Burgan · HRRR via **cfgrib + xarray** · numpy · rasterio · Leaflet 1.9 (dashboard)

Data sources: USGS 3DEP (public), LANDFIRE (public), NOAA HRRR via Big Data Project S3 (free), VIIRS active fire via NASA FIRMS API (free, key required).

---

## Reproduce

```bash
# Full pipeline (~12 min, downloads ~1.2 GB):
py scripts/simulate.py

# Blow-up phase only (48 h):
py scripts/simulate.py --hours 48

# Skip ETL, just rebuild the dashboard JSON from cached state:
py scripts/simulate.py --rebuild-dashboard
py scripts/_make_dashboard_data.py
```

[Dashboard ›](./)
