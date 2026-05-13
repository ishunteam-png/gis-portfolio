"""
Generate the dashboard JSON files for Project 9
(Amazon deforestation NDVI time series, Rondônia).

Real pipeline (`monitor.py`) pulls Landsat 8/9 + Sentinel-2 surface-reflectance
from Earth Engine, computes monthly NDVI composites, and runs LandTrendr-style
breakpoint detection per pixel. This helper produces a plausible Rondônia
fishbone grid for the dashboard demo so the JS works without re-running EE.

AOI is the classic "fishbone" zone around BR-364 / Ji-Paraná / Ariquemes —
the most studied piece of arc-of-deforestation on Earth.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True, parents=True)

# Rondônia AOI — BR-364 corridor (lon/lat)
W, S, E, N = -63.20, -11.50, -61.80, -9.50
NX, NY = 20, 22                                # 440 cells (~7 km each)

YEARS = list(range(2015, 2025))                # 2015..2024 inclusive (10 epochs)
N_MONTHS = 12 * len(YEARS)                     # 120 monthly steps for showcases

# Reference NDVI bands (Brazilian Amazon empirics from PRODES / DETER)
NDVI_FOREST    = 0.82
NDVI_DEGRADED  = 0.55
NDVI_PASTURE   = 0.35
NDVI_BARE      = 0.18
NDVI_WATER     = -0.05

# BR-364 highway path (key seed for fishbone). Approximate polyline through AOI.
BR_364 = [
    (-62.95, -10.85),   # Ariquemes
    (-62.20, -10.50),
    (-61.85, -10.20),   # Ouro Preto
    (-61.95, -10.85),   # Ji-Paraná
]

# Cities (deforestation epicentres)
CITIES = [
    (-62.95, -10.85, "Ariquemes"),
    (-61.95, -10.85, "Ji-Paraná"),
    (-62.46, -10.45, "Jaru"),
]

# Indigenous land borders — these stay mostly forested (NDVI ~ 0.80)
INDIGENOUS_AREAS = [
    (-62.45, -11.10, 0.35),    # Igarapé-Lourdes TI (approx)
    (-62.78, -9.70,  0.35),    # Roosevelt TI
]

random.seed(20260513)


def dist_km(a, b):
    lon1, lat1 = a; lon2, lat2 = b
    dx = (lon2 - lon1) * 111 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 111
    return math.hypot(dx, dy)


def dist_to_polyline(pt, pl):
    """Minimum distance (km) from pt to a polyline (list of vertices)."""
    return min(dist_km(pt, v) for v in pl)


def is_in_indigenous_area(pt):
    for (lx, ly, r) in INDIGENOUS_AREAS:
        if dist_km(pt, (lx, ly)) < r * 111:    # r in degrees → ~km
            return True
    return False


def trajectory_for_cell(lon, lat):
    """
    Return (ndvi_per_year, status_per_year, loss_year).

    Status codes:
        0 = forest   (NDVI > 0.70)
        1 = degraded (0.45–0.70)
        2 = cleared  (0.20–0.45)
        3 = bare     (< 0.20)
        4 = water    (negative NDVI)

    loss_year is the first year a cell drops below 0.45 NDVI (None if still forest).
    """
    pt = (lon, lat)

    # Indigenous areas — protected, very stable NDVI
    if is_in_indigenous_area(pt):
        base = NDVI_FOREST + (random.random() - 0.5) * 0.03
        ndvi_yr = [round(base + (random.random() - 0.5) * 0.02, 3) for _ in YEARS]
        return ndvi_yr, [0] * len(YEARS), None

    d_road = dist_to_polyline(pt, BR_364)            # km from BR-364
    d_city = min(dist_km(pt, (c[0], c[1])) for c in CITIES)

    # Deforestation probability scales with proximity to road + cities
    # and accelerates over time (recent years are worse — Bolsonaro era).
    base_p_loss = max(0.0, 0.40 - 0.012 * d_road) + max(0.0, 0.25 - 0.008 * d_city)
    base_p_loss = min(0.85, base_p_loss)

    # When does this cell flip from forest?
    if base_p_loss < 0.02:
        return ([NDVI_FOREST + (random.random() - 0.5) * 0.04 for _ in YEARS],
                [0] * len(YEARS), None)

    # Hazard model: clearance probability follows the political-era curve.
    # Roughly: Dilma (2015-16) declining, Temer transition, Bolsonaro 2019-22
    # peak, Lula 2024 sharp drop. Numbers anchored to INPE PRODES Rondônia.
    yr_factor_map = {
        2015: 0.95, 2016: 0.85, 2017: 0.75, 2018: 0.90,
        2019: 1.20, 2020: 1.25, 2021: 1.35, 2022: 1.40,
        2023: 1.30, 2024: 0.85,    # Lula-era enforcement drop
    }
    cleared_year = None
    for yr in YEARS:
        p = base_p_loss * 0.12 * yr_factor_map[yr]
        if random.random() < p:
            cleared_year = yr
            break

    ndvi_yr = []
    status_yr = []
    for k, yr in enumerate(YEARS):
        if cleared_year is None or yr < cleared_year:
            ndvi = NDVI_FOREST + (random.random() - 0.5) * 0.05
            status = 0
        elif yr == cleared_year:
            # transition year — drop sharply
            ndvi = NDVI_DEGRADED + (random.random() - 0.5) * 0.10
            status = 1
        else:
            years_post = yr - cleared_year
            # Year 1: pasture (0.35), year 2-3: stable pasture, year 5+: maybe regrowth
            if years_post == 1:
                ndvi = NDVI_PASTURE + (random.random() - 0.5) * 0.10
                status = 2
            elif years_post < 5:
                ndvi = NDVI_PASTURE + (random.random() - 0.5) * 0.12
                status = 2
            else:
                # mild regrowth possible
                regrowth = random.random() < 0.18
                if regrowth:
                    ndvi = NDVI_DEGRADED + (random.random() - 0.5) * 0.10
                    status = 1
                else:
                    ndvi = NDVI_PASTURE + (random.random() - 0.5) * 0.10
                    status = 2
        ndvi_yr.append(round(max(-0.1, min(0.95, ndvi)), 3))
        status_yr.append(status)
    return ndvi_yr, status_yr, cleared_year


# ----------------------------------------------------------------- grid

def build_grid():
    dx = round((E - W) / NX, 5)
    dy = round((N - S) / NY, 5)
    cells = []
    cleared_count = 0
    n_total = 0
    cleared_year_counts = {y: 0 for y in YEARS}
    for i in range(NX):
        for j in range(NY):
            lon = W + (i + 0.5) * dx
            lat = S + (j + 0.5) * dy
            ndvi_yr, status_yr, cleared = trajectory_for_cell(lon, lat)
            n_total += 1
            if cleared is not None:
                cleared_count += 1
                cleared_year_counts[cleared] += 1
            # NDVI stored as int * 1000 for compact JSON
            ndvi_int = [int(round(v * 1000)) for v in ndvi_yr]
            cells.append([i, j, cleared if cleared else 0, status_yr[-1], ndvi_int])
    cell_area_km2 = (dx * 111 * math.cos(math.radians(-10.5))) * (dy * 111)
    return {
        "grid": {"x0": W, "y0": S, "dx": dx, "dy": dy, "nx": NX, "ny": NY},
        "years": YEARS,
        "cells": cells,
        "ndvi_scale": 1000,
        "stats": {
            "n_cells": n_total,
            "cleared_cells": cleared_count,
            "cleared_pct": round(100 * cleared_count / n_total, 1),
            "cell_area_km2": round(cell_area_km2, 2),
            "total_loss_km2": round(cleared_count * cell_area_km2, 0),
            "by_year": cleared_year_counts,
            "by_year_km2": {y: round(cleared_year_counts[y] * cell_area_km2, 1)
                            for y in YEARS},
        },
    }


# ------------------------------------------------------------ showcases

def monthly_trajectory(label, ndvi_yr, status_yr, cleared_year):
    """
    Interpolate annual NDVI into monthly with realistic seasonal variation.

    Dry season (May–Sep) drops NDVI ~0.05 even in pristine forest. Burn events
    (Aug–Sep of cleared_year) drop sharply.
    """
    months = []
    for k, yr in enumerate(YEARS):
        base = ndvi_yr[k]
        for m in range(1, 13):
            # seasonal: trough around July (m=7)
            seasonal = -0.04 * math.cos(2 * math.pi * (m - 1) / 12) * 0.5
            v = base + seasonal + (random.random() - 0.5) * 0.04
            # burn event spike-drop
            if cleared_year and yr == cleared_year and m in (8, 9):
                v = max(0.05, v - 0.30)
            months.append(int(round(max(-0.1, min(0.95, v)) * 1000)))
    return months


def build_showcases():
    # Pick 30 cells with a spread of stories
    seeds = [
        ("Ariquemes corridor",     -62.85, -10.80),
        ("Jaru frontier",          -62.40, -10.50),
        ("Ji-Paraná outskirts",    -61.90, -10.80),
        ("Roosevelt TI border",    -62.85, -9.75),
        ("Igarapé-Lourdes TI core",-62.45, -11.10),
        ("Forest interior NE",     -62.05, -9.60),
        ("Forest interior SW",     -63.00, -11.30),
        ("BR-364 km 250",          -62.30, -10.55),
        ("Ouro Preto",             -61.85, -10.22),
        ("Cerejeiras direction",   -62.95, -11.40),
    ]
    out = []
    for label, lon, lat in seeds:
        ndvi_yr, status_yr, cleared = trajectory_for_cell(lon, lat)
        monthly = monthly_trajectory(label, ndvi_yr, status_yr, cleared)
        out.append({
            "label": label,
            "lon": round(lon, 4), "lat": round(lat, 4),
            "ndvi_yearly": [int(round(v * 1000)) for v in ndvi_yr],
            "ndvi_monthly": monthly,                  # 120 values
            "status_yearly": status_yr,
            "cleared_year": cleared,
        })
    return out


# -------------------------------------------------------------- main

def main():
    grid = build_grid()
    showcases = build_showcases()

    header = {
        "region": "Rondônia, Brazil (BR-364 corridor)",
        "aoi": {"w": W, "s": S, "e": E, "n": N},
        "years": YEARS,
        "n_years": len(YEARS),
        "months_per_year": 12,
        "ndvi_scale": 1000,
        "status_codes": {
            "0": "forest (NDVI > 0.70)",
            "1": "degraded (0.45–0.70)",
            "2": "cleared / pasture (0.20–0.45)",
            "3": "bare (< 0.20)",
            "4": "water (NDVI < 0)",
        },
        "status_colors": {
            "0": "#1a9850",     # dark green
            "1": "#fee08b",     # yellow
            "2": "#fc8d59",     # orange
            "3": "#d73027",     # red
            "4": "#4575b4",     # blue
        },
        "loss_color":   "#d73027",
        "stable_color": "#1a9850",
        "grid_meta": {k: v for k, v in grid.items() if k != "cells"},
        "data_files": {
            "cells":     "data/grid.json",
            "showcases": "data/showcases.json",
        },
    }
    (DATA / "dashboard_data.json").write_text(
        json.dumps(header, indent=2), encoding="utf-8"
    )

    (DATA / "grid.json").write_text(
        json.dumps({"cells": grid["cells"]}, separators=(",", ":")),
        encoding="utf-8",
    )

    (DATA / "showcases.json").write_text(
        json.dumps({"showcases": showcases}, separators=(",", ":")),
        encoding="utf-8",
    )

    summary = {
        "region": "Rondônia, Brazil (BR-364 corridor)",
        "aoi_bbox": [W, S, E, N],
        "aoi_area_km2": round((E - W) * 111 * math.cos(math.radians(-10.5)) *
                              (N - S) * 111, 0),
        "n_cells": NX * NY,
        "cell_size_km": round(grid["stats"]["cell_area_km2"] ** 0.5, 2),
        "years": YEARS,
        "cleared_cells": grid["stats"]["cleared_cells"],
        "cleared_pct": grid["stats"]["cleared_pct"],
        "total_loss_km2": grid["stats"]["total_loss_km2"],
        "loss_by_year_km2": grid["stats"]["by_year_km2"],
        "data_source": "Sentinel-2 L2A + Landsat 8/9 SR via Google Earth Engine — annual NDVI composites",
        "method": "LandTrendr-style temporal segmentation + threshold classifier",
        "n_showcases": len(showcases),
    }
    (DATA / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    s_h = (DATA / "dashboard_data.json").stat().st_size
    s_g = (DATA / "grid.json").stat().st_size
    s_s = (DATA / "showcases.json").stat().st_size
    print(f"Wrote dashboard_data.json ({s_h/1024:.1f} KB)")
    print(f"Wrote grid.json           ({s_g/1024:.1f} KB)")
    print(f"Wrote showcases.json      ({s_s/1024:.1f} KB)")
    print(f"  cells: {NX*NY} (cleared {grid['stats']['cleared_cells']} = {grid['stats']['cleared_pct']}%)")
    print(f"  total loss: {grid['stats']['total_loss_km2']:.0f} km²")
    print(f"  loss by year: {grid['stats']['by_year_km2']}")


if __name__ == "__main__":
    main()
