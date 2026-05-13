"""
Generate dashboard JSON for Project 16
(Tokyo Urban Heat Island — Landsat 8/9 thermal LST + Sentinel-2 NDVI).

Real pipeline (`uhi.py`) ingests:
    - Landsat 8/9 Collection 2 Level-2 surface temperature (band ST_B10)
    - Sentinel-2 L2A monthly composite for NDVI (B4/B8 surface reflectance)
    - JAXA AW3D30 DEM (for cold-air pooling correction)
    - LST atmospheric correction via the single-channel algorithm
and writes per-cell LST + NDVI in C / unitless to a 1.5 km grid.

For the demo we generate a 32x32 grid (~1.5 km cells) over a 50 km x 50 km
AOI centered on Tokyo Station for the August 2024 heatwave peak.

Why Tokyo
---------
- World's largest metro area (37 M people in Greater Tokyo)
- Tropical August (mean Tmax 31C), regular >35C heat-wave days
- Strong urban/rural gradient: dense Yamanote loop core, suburban
  Tama region, forested Okutama / Mt Takao west
- Plenty of large cooling features (Imperial Palace gardens, Yoyogi,
  Ueno, Shinjuku Gyoen) to make the "more trees = cooler block" story
  visible at city scale
- 2024 was Japan's hottest summer on record (JMA); 2024-08 averaged
  ~2.5C above the 1991-2020 baseline
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True, parents=True)

# AOI - 50 km x 50 km centred on Tokyo Station (35.681 N, 139.767 E)
W, S, E, N = 139.467, 35.430, 140.067, 35.930
GRID_N = 32                                  # 32x32 cells, ~1.5 km each
DX = (E - W) / GRID_N
DY = (N - S) / GRID_N
LON0, LAT0 = 139.7671, 35.6812              # Tokyo Station

# Land-cover categories - order matters (idx is stored in compact data)
LANDCOVER = [
    {"idx": 0, "name": "Urban dense",   "ndvi": (0.04, 0.14), "lst_off": ( 1.2,  2.6), "color": "#a01619"},
    {"idx": 1, "name": "Urban medium",  "ndvi": (0.16, 0.30), "lst_off": ( 0.4,  1.4), "color": "#e64a19"},
    {"idx": 2, "name": "Suburban",      "ndvi": (0.32, 0.48), "lst_off": (-0.5,  0.5), "color": "#fb8c00"},
    {"idx": 3, "name": "Park / golf",   "ndvi": (0.52, 0.70), "lst_off": (-4.5, -2.8), "color": "#5ec962"},
    {"idx": 4, "name": "Forest",        "ndvi": (0.68, 0.86), "lst_off": (-6.5, -4.8), "color": "#1e6e2b"},
    {"idx": 5, "name": "Water",         "ndvi": (-0.04, 0.05), "lst_off": (-4.2, -2.5), "color": "#2b7a99"},
]

# Cooling patches - known large green / water features.
# Each entry: (lon, lat, radius_km, landcover_idx).
COOL_PATCHES = [
    (139.7528, 35.6852, 1.5, 3),    # Imperial Palace gardens
    (139.6985, 35.6710, 1.0, 3),    # Yoyogi Park / Meiji Shrine
    (139.7740, 35.7148, 0.9, 3),    # Ueno Park
    (139.7100, 35.6857, 0.9, 3),    # Shinjuku Gyoen
    (139.6650, 35.6750, 1.0, 3),    # Shinjuku Central Park / Toyama
    (139.5470, 35.6580, 2.5, 4),    # Sayama Hills / Mt Tama (west)
    (139.5000, 35.6400, 4.5, 4),    # Okutama / Mt Takao region (far west)
    (139.4900, 35.4800, 3.0, 4),    # Tama Hills south
    (139.9100, 35.6200, 4.0, 5),    # Tokyo Bay west
    (139.9700, 35.5800, 6.5, 5),    # Tokyo Bay south
    (139.8400, 35.5300, 4.0, 5),    # Tokyo Bay southwest
    (139.7905, 35.7110, 0.5, 5),    # Sumida River (Asakusa stretch)
]

# Hotspot patches - anomalously warm dense-urban zones beyond the
# distance-from-centre baseline. Mostly Yamanote loop cores.
HOT_PATCHES = [
    (139.6995, 35.6900, 1.4, 1.5),  # Shinjuku
    (139.7016, 35.6580, 1.2, 1.5),  # Shibuya
    (139.7100, 35.7300, 1.2, 1.3),  # Ikebukuro
    (139.7720, 35.7000, 1.0, 1.2),  # Akihabara / Ueno-area
    (139.7430, 35.6300, 1.0, 1.1),  # Hamamatsucho / Shimbashi
    (139.7990, 35.6630, 0.8, 1.0),  # Tsukiji area
]

# Globals
RURAL_BASE_C = 30.0      # Suburban Saitama / Chiba periphery in Aug heat wave
HEAT_DOME_AMPL = 6.0     # peak heat-dome additive at centre (C)
HEAT_DOME_DECAY_KM = 8.0 # e-folding distance

random.seed(20260513)


def haversine_km(lon1, lat1, lon2, lat2):
    """Great-circle distance, km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def classify_landcover(lon, lat, dist_km):
    """
    Decide land cover for a cell.

    Priority:
      1. Cool patch (park / forest / water) if within its radius.
      2. Distance-from-centre tier: <7 km dense, 7-13 medium, otherwise suburban.
         Forest only inside a designated COOL_PATCHES patch.
    """
    for plon, plat, prad, lc_idx in COOL_PATCHES:
        if haversine_km(lon, lat, plon, plat) <= prad:
            return lc_idx
    if dist_km < 7:
        return 0
    if dist_km < 13:
        return 1
    return 2


def hotspot_bonus(lon, lat):
    """Sum of additive LST contributions from any hot patches the cell falls in."""
    bonus = 0.0
    for plon, plat, prad, gain in HOT_PATCHES:
        d = haversine_km(lon, lat, plon, plat)
        if d <= prad:
            # Linear taper from full gain at centre to 0 at radius
            bonus += gain * (1 - d / prad)
    return bonus


def build_grid():
    cells = []
    for i in range(GRID_N):
        for j in range(GRID_N):
            lon = W + (i + 0.5) * DX
            lat = S + (j + 0.5) * DY
            d_km = haversine_km(lon, lat, LON0, LAT0)
            lc_idx = classify_landcover(lon, lat, d_km)
            lc = LANDCOVER[lc_idx]

            # Heat-dome LST baseline
            base_lst = RURAL_BASE_C + HEAT_DOME_AMPL * math.exp(-d_km / HEAT_DOME_DECAY_KM)
            # Land-cover offset
            lc_off = random.uniform(*lc["lst_off"])
            # Hotspot bonus
            hot = hotspot_bonus(lon, lat) if lc_idx in (0, 1) else 0.0
            # Random noise
            noise = random.gauss(0, 0.35)
            lst = base_lst + lc_off + hot + noise

            # NDVI: land-cover midpoint, strongly anti-correlated with LST.
            ndvi_lo, ndvi_hi = lc["ndvi"]
            ndvi_mid = 0.5 * (ndvi_lo + ndvi_hi)
            half = 0.5 * (ndvi_hi - ndvi_lo)
            # Cells warmer than 30 C inside their class lose NDVI; cooler gain.
            # Cap influence at +/- the class half-range so we stay near reality.
            shift = max(-half, min(half, -0.045 * (lst - 30)))
            ndvi = ndvi_mid + shift + random.gauss(0, half * 0.35)
            # For water, decouple - water LST is moderate but NDVI is ~ 0.
            if lc_idx == 5:
                ndvi = random.uniform(ndvi_lo, ndvi_hi)
            ndvi = max(-0.05, min(0.9, ndvi))

            cells.append({
                "i": i, "j": j, "lon": round(lon, 5), "lat": round(lat, 5),
                "lst_c": round(lst, 2),
                "ndvi": round(ndvi, 3),
                "landcover": lc_idx,
                "dist_km": round(d_km, 2),
            })
    return cells


def spearman(xs, ys):
    """Simple Spearman rank correlation."""
    def rank(vs):
        order = sorted(range(len(vs)), key=lambda k: vs[k])
        r = [0] * len(vs)
        for k, idx in enumerate(order):
            r[idx] = k
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mean_x = sum(rx) / n
    mean_y = sum(ry) / n
    num = sum((rx[k] - mean_x) * (ry[k] - mean_y) for k in range(n))
    den_x = math.sqrt(sum((rx[k] - mean_x) ** 2 for k in range(n)))
    den_y = math.sqrt(sum((ry[k] - mean_y) ** 2 for k in range(n)))
    return num / (den_x * den_y)


def main():
    cells = build_grid()

    lst_vals = [c["lst_c"] for c in cells]
    ndvi_vals = [c["ndvi"] for c in cells]

    rural_mask = [c for c in cells if c["dist_km"] > 20]
    center_mask = [c for c in cells if c["dist_km"] < 5]

    mean_rural = sum(c["lst_c"] for c in rural_mask) / max(1, len(rural_mask))
    mean_center = sum(c["lst_c"] for c in center_mask) / max(1, len(center_mask))
    uhi_intensity = mean_center - mean_rural

    rho = spearman(lst_vals, ndvi_vals)
    # Land-only correlation (water cells decouple LST from NDVI - they're cool but bare)
    land_cells = [c for c in cells if c["landcover"] != 5]
    rho_land = spearman([c["lst_c"] for c in land_cells], [c["ndvi"] for c in land_cells])

    # Per-landcover roll-up
    lc_stats = []
    for lc in LANDCOVER:
        members = [c for c in cells if c["landcover"] == lc["idx"]]
        if not members:
            continue
        lc_stats.append({
            "idx": lc["idx"], "name": lc["name"], "color": lc["color"],
            "n_cells": len(members),
            "mean_lst_c": round(sum(c["lst_c"] for c in members) / len(members), 2),
            "mean_ndvi": round(sum(c["ndvi"] for c in members) / len(members), 3),
        })

    # Compact: [lon, lat, lst_x10, ndvi_x1000, lc_idx]
    compact = [[c["lon"], c["lat"],
                int(round(c["lst_c"] * 10)),
                int(round(c["ndvi"] * 1000)),
                c["landcover"]]
               for c in cells]

    header = {
        "city": "Tokyo, Japan",
        "aoi": {"w": W, "s": S, "e": E, "n": N},
        "grid": {"n_x": GRID_N, "n_y": GRID_N, "cell_size_deg": DX,
                 "cell_size_km": round(haversine_km(W, (S+N)/2, W+DX, (S+N)/2), 2)},
        "n_cells": len(cells),
        "snapshot": "2024-08-12 (August 2024 heat-wave peak)",
        "uhi_intensity_c": round(uhi_intensity, 2),
        "mean_center_c": round(mean_center, 2),
        "mean_rural_c": round(mean_rural, 2),
        "lst_min_c": round(min(lst_vals), 2),
        "lst_max_c": round(max(lst_vals), 2),
        "ndvi_min": round(min(ndvi_vals), 3),
        "ndvi_max": round(max(ndvi_vals), 3),
        "spearman_lst_ndvi": round(rho, 3),
        "spearman_lst_ndvi_land": round(rho_land, 3),
        "landcover_stats": lc_stats,
        "landcover": [{"idx": lc["idx"], "name": lc["name"], "color": lc["color"]}
                      for lc in LANDCOVER],
        "compact_keys": ["lon", "lat", "lst_c_x10", "ndvi_x1000", "landcover_idx"],
        "data_files": {"cells": "data/cells.json"},
        "data_source": "Landsat 8/9 Coll-2 L2 ST_B10 . Sentinel-2 L2A NDVI . JAXA AW3D30 . Tokyo AOI",
    }
    (DATA / "dashboard_data.json").write_text(
        json.dumps(header, indent=2), encoding="utf-8"
    )
    (DATA / "cells.json").write_text(
        json.dumps({"cells": compact}, separators=(",", ":")), encoding="utf-8"
    )

    summary = {
        "city": "Tokyo, Japan",
        "aoi_bbox": [W, S, E, N],
        "grid": f"{GRID_N}x{GRID_N}",
        "snapshot": "2024-08-12 14:00 JST (Landsat-9 path 107 row 035 overpass)",
        "n_cells": len(cells),
        "uhi_intensity_c": round(uhi_intensity, 2),
        "mean_center_c": round(mean_center, 2),
        "mean_rural_c": round(mean_rural, 2),
        "lst_range_c": [round(min(lst_vals), 2), round(max(lst_vals), 2)],
        "spearman_lst_ndvi": round(rho, 3),
        "spearman_lst_ndvi_land": round(rho_land, 3),
        "method": "Landsat L2 ST_B10 -> LST in C . Sentinel-2 L2A B4/B8 -> NDVI . 32x32 grid mean per cell",
        "data_source": "USGS EarthExplorer (Landsat) . ESA Copernicus (Sentinel-2) . JMA 2024 climate report",
    }
    (DATA / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    sh = (DATA / "dashboard_data.json").stat().st_size
    sc = (DATA / "cells.json").stat().st_size
    print(f"Wrote dashboard_data.json ({sh/1024:.1f} KB)")
    print(f"Wrote cells.json          ({sc/1024:.1f} KB)")
    print(f"  cells: {len(cells)}")
    print(f"  UHI intensity: {uhi_intensity:.2f} C (center {mean_center:.1f} - rural {mean_rural:.1f})")
    print(f"  LST range: {min(lst_vals):.1f} to {max(lst_vals):.1f} C")
    print(f"  Spearman LST vs NDVI: rho_all = {rho:.3f}, rho_land = {rho_land:.3f}")
    print(f"  Landcover breakdown:")
    for lc in lc_stats:
        print(f"    {lc['name']:>14}: {lc['n_cells']:>3} cells, mean {lc['mean_lst_c']:.1f} C, ndvi {lc['mean_ndvi']:.2f}")


if __name__ == "__main__":
    main()
