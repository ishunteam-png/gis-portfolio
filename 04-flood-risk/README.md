# Project 4 — Jakarta Compound Flood Risk

Jakarta is the worst place on Earth to ignore flood risk. 40% of the city sits below sea level. The northern wards subside at 10–25 cm per year, which is honestly hard to believe until you see it on InSAR. Thirteen rivers cross the city before discharging into the Java Sea. Monsoon rainfall and tidal pulses interact to produce compound floods that simple fluvial-only models miss. The Indonesian government's response to all of this is to *move the capital* — the new city Nusantara is being built ~1,300 km away in Borneo specifically because Jakarta isn't salvageable.

If a flood model works in Jakarta, it works anywhere.

![Jakarta flood-risk model, 4 panels](assets/flood_hero.png)

## The model

For every pixel in a 23 km × 26 km bbox covering central Jakarta, I compute a composite 0–1 risk index from four signals derived purely from terrain and OSM land-use:

| Signal | What it captures | Direction | Weight |
|---|---|---|---:|
| **HAND** (Height Above Nearest Drainage) | Fluvial baseline — how far you sit above the nearest river/canal | Lower → wetter | 0.40 |
| **Slope** (degrees, from DEM gradient) | Ponding accelerator — flat ground holds water | Lower → wetter | 0.25 |
| **Imperviousness** (sealed-surface LU within 500 m) | Runoff accelerator — asphalt doesn't absorb | Higher → wetter | 0.20 |
| **Drainage density** (waterway m/km² within 500 m) | Evacuation capacity — sparse drains → longer ponding | Lower → wetter | 0.15 |

Min-max normalise each (with the right direction), weighted sum, quantile-band the result into 4 risk classes (low / moderate / high / very-high).

DEM comes from the Mapzen open elevation tiles. OSM provides the waterways, the impervious and pervious land-use polygons, and the critical infrastructure. Everything is free.

## Why a 4-signal model, not just HAND

A pure-HAND model gives you the fluvial baseline — how far above the nearest channel you sit. That's the dominant signal in deep-valley cities like Tbilisi, where the Mtkvari runs through a defined gorge. In a flat coastal delta like Jakarta, HAND alone misses too much:

- A flat parking lot accumulates standing water *regardless* of its distance to a river. Slope captures that.
- Jakarta's mid-city neighbourhoods are 80–95% sealed surface; 100 mm of rain becomes ≈90 mm of runoff there, vs ≈30 mm in a permeable suburb. Imperviousness captures that.
- Kampung-style neighbourhoods with sparse storm drains pond for *days* longer than planned grids with regular drainage cross-sections, even at the same HAND value. Drainage density captures that.

Combining all four captures the compound mechanism: river overflow + intense convective rainfall + sealed surfaces + clogged drains. That's why the high-risk band in panel 1 of the hero map lines up not just with rivers but also with dense kampung neighbourhoods.

## What this gives you

The headline number for an emergency-management agency:

![Critical infrastructure exposure by asset type](assets/critical_infra_chart.png)

| Asset type | In high + very-high band |
|---|---:|
| Schools | **1,360** |
| Kindergartens | **725** |
| Clinics | **627** |
| Hospitals | **138** |
| Police stations | **105** |
| Universities + colleges | **128** |
| Fire stations | **45** |
| Ambulance stations | **22** |

That's a screening map for triaging *which buildings to harden first*. Not a flood-depth simulation — those need a proper 2D hydraulic solver — but a defensible first-pass ranking of where the hazard concentrates.

## Component diagnostics

![All four normalised inputs](assets/risk_components.png)

Each of the four contributions, normalised, side-by-side. Useful for auditing the weighting — if one signal swamped the composite I'd see it here.

## What I learned the hard way

A few things broke that are worth documenting:

1. **Jakarta has too many OSM buildings to pull in one Overpass query.** I made the request, it ran for 30 minutes, then returned 0 features without an error. I caught this when the building exposure chart showed all-zero columns. The fix is to chunk the bbox into a 2×3 grid and pull each chunk separately; that's what `scripts/patch_buildings.py` does. Even better: skip OSM and use the Microsoft Building Footprints open dataset (28M buildings for Indonesia).

2. **The Euclidean-nearest HAND I'm computing is not the proper HAND.** Real HAND follows the *flow path* to the drainage. A pixel on the wrong side of a ridge gets matched to a stream on its side of the ridge by Euclidean distance, even though hydrologically it drains the other way. The result is some negative HAND values where pixels are below the elevation of the "nearest" drainage — a topological artefact. I drop the negatives before building flood masks, which is a workaround, not a fix. The real fix is a D8 flow-routing step from WhiteboxTools.

3. **The CRS situation around Mapzen tiles is fiddly.** Tiles come in EPSG:3857. OSM is in EPSG:4326. The Folium overlay needs the risk-band raster reprojected to 4326. `rasterio.warp.calculate_default_transform` does this but the math for the corner bounds is unintuitive. A few attempts produced overlays that were geographically offset by ~500 m before I worked out the right inversion.

## The interactive map

The [dashboard for this project](https://ishunteam-png.github.io/gis-portfolio/04-flood-risk/) lets you toggle the risk-band overlay, filter critical-infra markers by risk band, and click any school/hospital to see its exposure.

## What I'd do next

- **Proper HAND** via D8 flow routing. WhiteboxTools' chain is `BreachDepressions → D8Pointer → D8FlowAccumulation → ElevationAboveStream`. Drop-in replacement for my Euclidean proxy.
- **Coastal storm-surge layer**, because Jakarta's compound floods include sea-level pulses propagating up the rivers. The GTSM global tide-and-surge model has output that could be combined with the fluvial HAND.
- **Subsidence baseline.** North Jakarta sinks 25 cm/yr. That moves the flood baseline by 1.25 m every five years. Adding a Project-1-style InSAR layer for Jakarta would let the risk map be re-baselined annually.
- **Population, not just buildings.** Joining with WorldPop or HRSL gives "X residents in band Y", which is the number that actually drives policy.
- **Historical-event validation.** Jakarta's 2007, 2013, 2020 floods have public extent maps. Overlaying them against my high+very-high band would give a hit-rate / Critical Success Index, which is the real test of any flood model.

This is a *screening* map. Items 1, 2, 4, 5 above are what would turn it into a *planning* map.
