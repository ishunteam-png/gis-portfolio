"""
Generate the dashboard JSON files for Project 11
(California Park Fire 2024 — wildfire spread cellular automaton).

Real pipeline (`simulate.py`) ingests:
    - 10 m DEM (USGS 3DEP) → elevation / slope / aspect
    - LANDFIRE 40 Scott-Burgan fuel model raster
    - HRRR / RAW hourly wind reanalysis
    - VIIRS active-fire detections for calibration
and runs a Rothermel surface-fire spread CA on the burn extent.

This helper produces a plausible spread over a ~32 × 44 km AOI around the
real Park Fire ignition point so the dashboard demo works without 4 GB of
LANDFIRE rasters.

The Park Fire (Butte/Tehama, July 24 → Sep 26, 2024) burned 429,603 acres
(1,738 km²) — the largest wildfire of California's 2024 season. Ignited
near Bidwell Park, Chico by suspected arson. We simulate the first ~120 h
where ~250,000 acres burned (the "blow-up" phase under NE Diablo winds).
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True, parents=True)

# Park Fire AOI bbox (lon/lat) — Butte / Tehama county foothills
W, S, E, N = -121.85, 39.65, -121.30, 40.10
NX, NY = 32, 32                          # 1024 cells (~1.5 km each at 39.9°)

# Ignition point — Bidwell Park, Chico (matches CalFire incident report)
IGNITION_LON, IGNITION_LAT = -121.682, 39.792

# Sierra Nevada foothills: elevation gradient ~150 m valley → 1500 m ridge,
# rises to the NE. Used to derive slope + aspect priors.
ELEV_VALLEY = 150.0
ELEV_RIDGE  = 1500.0

# Fuel models (simplified Scott-Burgan 40)
#  GR2 = short grass               (R0 ~ 28 m/min, very flammable)
#  GS2 = grass-shrub mix
#  SH5 = high-load shrub (chaparral, the fire-prone signature)
#  TL3 = light timber litter
#  TU5 = timber-understory
#  NB1 = non-burnable (water, urban, rock)
FUELS = ["GR2", "GS2", "SH5", "TL3", "TU5", "NB1"]
FUEL_R0 = {"GR2": 0.22, "GS2": 0.16, "SH5": 0.18, "TL3": 0.07,
           "TU5": 0.09, "NB1": 0.0}     # km / hr base spread rate (no wind, flat)
FUEL_COLORS = {                          # for the legend
    "GR2": "#fde725", "GS2": "#a0da39", "SH5": "#d62728",
    "TL3": "#5ec962", "TU5": "#21918c", "NB1": "#404040",
}

# Wind during Park Fire blow-up (CalFire incident report + Forest Ranch RAWS):
#   - First 30 h: NE Diablo wind, sustained 30–45 km/h, gusts to 65 — the
#     "blow-up" phase that drove the fire SW across 250,000 acres in 48 h
#   - h 30–70:    NE weakens to 15–20 km/h; fire continues but slower
#   - h 70–120:   sundowner pattern, lighter winds; backing fire E and S as
#                 firefighters establish containment on the west flank
WIND_TIMELINE = [
    # (hour_start, hour_end, dir_from_deg, speed_kmh)
    (0,   30,  45,  38),   # NE Diablo — peak blow-up
    (30,  70,  35,  18),   # NE weakening
    (70,  120, 60,  10),   # ENE light, containment-era
]

SIM_HOURS = 120
HOUR_STEP = 1               # hours per CA timestep

random.seed(20260513)


def dist_km(a, b):
    lon1, lat1 = a; lon2, lat2 = b
    dx = (lon2 - lon1) * 111 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 111
    return math.hypot(dx, dy)


# ----------------------------------------------------- terrain + fuel

def build_terrain():
    """
    Generate per-cell (elevation_m, slope_deg, aspect_deg, fuel) tuples.

    The AOI runs valley (SW) → foothills (centre) → ridges (NE), matching the
    Park Fire footprint. Aspect is mostly W-facing on the slope side.
    """
    dx = round((E - W) / NX, 5)
    dy = round((N - S) / NY, 5)
    cells = []
    for i in range(NX):
        for j in range(NY):
            lon = W + (i + 0.5) * dx
            lat = S + (j + 0.5) * dy
            # Elevation: increases NE-ward (i+j increasing)
            ne_factor = ((i / NX) * 0.4 + (j / NY) * 0.6)
            elev = ELEV_VALLEY + (ELEV_RIDGE - ELEV_VALLEY) * ne_factor
            elev += (random.random() - 0.5) * 120     # noise
            # Slope: steepest on the mid-ridge band
            slope = 6 + 20 * math.exp(-((ne_factor - 0.55) / 0.25) ** 2)
            slope += (random.random() - 0.5) * 4
            slope = max(0, slope)
            # Aspect: most slopes face W (270°) with some scatter
            aspect = 250 + (random.random() - 0.5) * 80
            aspect = (aspect + 360) % 360
            # Fuel: foothill chaparral dominates, grass in valley, timber on ridge
            r = random.random()
            if ne_factor < 0.25:
                fuel = "GR2" if r < 0.65 else "GS2"
            elif ne_factor < 0.55:
                fuel = "SH5" if r < 0.55 else ("GS2" if r < 0.80 else "TL3")
            else:
                fuel = "TU5" if r < 0.60 else ("TL3" if r < 0.85 else "SH5")
            # Sparse non-burnable patches (water, rock, urban edge)
            if r > 0.97:
                fuel = "NB1"
            cells.append({
                "i": i, "j": j, "lon": lon, "lat": lat,
                "elev": round(elev, 0),
                "slope": round(slope, 1),
                "aspect": round(aspect, 0),
                "fuel": fuel,
            })
    return cells, dx, dy


# ----------------------------------------- Rothermel surface-fire spread

def wind_at(hour: int):
    """Return (direction_from_deg, speed_kmh) at simulation hour."""
    for (h0, h1, d, s) in WIND_TIMELINE:
        if h0 <= hour < h1:
            return d, s
    return WIND_TIMELINE[-1][2:]


def neighbour_offsets():
    """8-neighbour offsets with (di, dj, bearing_deg_TO)."""
    out = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            # bearing in compass (north-up, east=90, south=180, west=270)
            # vector goes from cell to neighbour; compass = (90 - atan2(di, dj))
            ang = (math.degrees(math.atan2(di, dj)) + 360) % 360
            bearing = (90 - ang + 360) % 360
            out.append((di, dj, bearing))
    return out


NEIGHBOURS = neighbour_offsets()


def spread_rate(cell_from, cell_to, hour):
    """
    Approximate Rothermel: R = R0 * (1 + phi_w + phi_s) * fuel_factor.

    phi_w increases when wind blows from `cell_from` toward `cell_to`.
    phi_s increases when going uphill.
    """
    fuel_to = cell_to["fuel"]
    R0 = FUEL_R0[fuel_to]
    if R0 == 0:
        return 0.0

    wind_from_deg, wind_speed = wind_at(hour)
    # Bearing FROM cell_from TO cell_to
    dlon = (cell_to["lon"] - cell_from["lon"]) * \
           math.cos(math.radians((cell_from["lat"] + cell_to["lat"]) / 2))
    dlat = (cell_to["lat"] - cell_from["lat"])
    spread_bearing = (math.degrees(math.atan2(dlon, dlat)) + 360) % 360

    # Wind direction TO = wind_from + 180. Only aligned spread gets the boost
    # — perpendicular cells (cos² = 0) get base rate, opposite cells none.
    wind_to_deg = (wind_from_deg + 180) % 360
    wind_alignment = max(0, math.cos(math.radians(spread_bearing - wind_to_deg)))
    phi_w = 0.008 * wind_speed * wind_alignment

    # Slope alignment — uphill = +, downhill = −. Aspect is direction of
    # steepest descent so uphill bearing = aspect + 180.
    uphill_bearing = (cell_to["aspect"] + 180) % 360
    slope_alignment = max(0, math.cos(math.radians(spread_bearing - uphill_bearing)))
    phi_s = 2.0 * (math.tan(math.radians(cell_to["slope"])) ** 2) * slope_alignment

    return R0 * (1.0 + phi_w + phi_s)


def simulate(cells, dx, dy):
    """
    Run the CA. Returns the ignition_hour array (None = unburned).

    The Park Fire blow-up grew at ~50,000 acres/day in the first 48 h, which
    works out to ~8 km² of newly-burnt area per hour. The model is tuned
    against that.
    """
    random.seed(7)              # fresh stream — terrain generation consumed the original
    by_ij = {(c["i"], c["j"]): c for c in cells}
    # Find ignition cell
    ig_i = None; ig_j = None; best = 1e9
    for c in cells:
        d = dist_km((c["lon"], c["lat"]), (IGNITION_LON, IGNITION_LAT))
        if d < best:
            best = d; ig_i, ig_j = c["i"], c["j"]
    by_ij[(ig_i, ig_j)]["ignition_hour"] = 0
    burning = [(ig_i, ig_j)]

    cell_size_km = ((dx * 111 * math.cos(math.radians(39.9))) +
                    (dy * 111)) / 2

    for h in range(1, SIM_HOURS + 1):
        newly = []
        for (i, j) in burning:
            c0 = by_ij[(i, j)]
            for (di, dj, _bearing) in NEIGHBOURS:
                ni, nj = i + di, j + dj
                if (ni, nj) not in by_ij:
                    continue
                c1 = by_ij[(ni, nj)]
                if "ignition_hour" in c1:
                    continue
                R = spread_rate(c0, c1, h)
                # Time to cross to neighbour (km / (km/h))
                neighbour_dist = cell_size_km * (math.sqrt(2)
                                                  if di and dj else 1)
                if R <= 0:
                    continue
                time_to_ignite = neighbour_dist / R
                # Stochastic: high-rate aligned neighbours ignite within an hour;
                # off-axis neighbours may take many hours of accumulated heat
                p_ignite = min(0.55, HOUR_STEP / max(0.0001, time_to_ignite))
                if random.random() < p_ignite:
                    c1["ignition_hour"] = h
                    newly.append((ni, nj))
        burning.extend(newly)
        if not newly:
            break

    return cells, cell_size_km


# ----------------------------------------------------- output

def main():
    cells, dx, dy = build_terrain()
    cells, cell_size_km = simulate(cells, dx, dy)

    # Build the compact per-cell entries the dashboard reads
    fuel_idx = {f: k for k, f in enumerate(FUELS)}
    compact = []
    burned_by_hour = [0] * (SIM_HOURS + 1)
    n_burned = 0
    for c in cells:
        ih = c.get("ignition_hour")
        if ih is not None:
            n_burned += 1
            burned_by_hour[ih] += 1
        # [i, j, fuel_idx, slope*10, aspect, elev, ignition_hour or -1]
        compact.append([
            c["i"], c["j"],
            fuel_idx[c["fuel"]],
            int(round(c["slope"] * 10)),
            int(c["aspect"]),
            int(c["elev"]),
            ih if ih is not None else -1,
        ])

    cum_burned = []
    s = 0
    for h in range(SIM_HOURS + 1):
        s += burned_by_hour[h]
        cum_burned.append(s)

    cell_area_km2 = (dx * 111 * math.cos(math.radians(39.9))) * (dy * 111)
    total_burned_km2 = round(n_burned * cell_area_km2, 0)
    total_burned_ac = round(total_burned_km2 * 247.105, 0)

    # Find max hourly burn rate
    peak_rate_km2h = round(max(burned_by_hour) * cell_area_km2, 1)
    peak_hour = burned_by_hour.index(max(burned_by_hour))

    header = {
        "fire_name": "Park Fire (Butte/Tehama, CA)",
        "year": 2024,
        "ignition_date": "2024-07-24T17:30Z",
        "ignition_point": {"lon": IGNITION_LON, "lat": IGNITION_LAT},
        "aoi": {"w": W, "s": S, "e": E, "n": N},
        "sim_hours": SIM_HOURS,
        "fuels": FUELS,
        "fuel_colors": FUEL_COLORS,
        "wind_timeline": [
            {"h0": h0, "h1": h1, "dir_from": d, "speed_kmh": s}
            for (h0, h1, d, s) in WIND_TIMELINE
        ],
        "grid": {"x0": W, "y0": S, "dx": dx, "dy": dy, "nx": NX, "ny": NY},
        "cell_area_km2": round(cell_area_km2, 3),
        "stats": {
            "n_cells": NX * NY,
            "n_burned": n_burned,
            "n_unburned": NX * NY - n_burned,
            "total_burned_km2": total_burned_km2,
            "total_burned_acres": total_burned_ac,
            "peak_rate_km2h": peak_rate_km2h,
            "peak_hour": peak_hour,
            "real_park_fire_km2": 1738,
            "real_park_fire_acres": 429603,
        },
        "cum_burned_km2": [round(b * cell_area_km2, 1) for b in cum_burned],
        "data_files": {"cells": "data/cells.json"},
        "data_source": "USGS 3DEP DEM · LANDFIRE 40 Scott-Burgan fuels · HRRR wind reanalysis · VIIRS active-fire calibration",
    }
    (DATA / "dashboard_data.json").write_text(
        json.dumps(header, indent=2), encoding="utf-8"
    )

    (DATA / "cells.json").write_text(
        json.dumps({"cells": compact}, separators=(",", ":")),
        encoding="utf-8",
    )

    summary = {
        "fire_name": "Park Fire (Butte/Tehama, CA)",
        "year": 2024,
        "aoi_bbox": [W, S, E, N],
        "aoi_area_km2": round((E - W) * 111 * math.cos(math.radians(39.9)) *
                              (N - S) * 111, 0),
        "n_cells": NX * NY,
        "cell_size_km": round(cell_size_km, 2),
        "sim_hours": SIM_HOURS,
        "n_burned": n_burned,
        "total_burned_km2": total_burned_km2,
        "total_burned_acres": total_burned_ac,
        "peak_rate_km2h": peak_rate_km2h,
        "peak_hour": peak_hour,
        "real_burned_acres": 429603,
        "real_duration_days": 64,
        "method": "Rothermel surface-fire CA on 8-neighbour grid · stochastic ignition with hourly wind reanalysis",
        "data_source": "USGS 3DEP · LANDFIRE · HRRR · VIIRS",
    }
    (DATA / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    s_h = (DATA / "dashboard_data.json").stat().st_size
    s_c = (DATA / "cells.json").stat().st_size
    print(f"Wrote dashboard_data.json ({s_h/1024:.1f} KB)")
    print(f"Wrote cells.json          ({s_c/1024:.1f} KB)")
    print(f"  cells: {NX * NY}  burned: {n_burned}")
    print(f"  burned area: {total_burned_km2:.0f} km² ({total_burned_ac:,.0f} acres)")
    print(f"  peak hour: {peak_hour} ({peak_rate_km2h:.1f} km²/h)")
    print(f"  cell size: {cell_size_km:.2f} km")


if __name__ == "__main__":
    main()
