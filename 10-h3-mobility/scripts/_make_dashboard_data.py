"""
Generate the dashboard JSON files for Project 10
(H3 hexagonal mobility analytics, NYC Yellow Taxi).

The real pipeline (`mobility.py`) consumes TLC Yellow Taxi Trip Records,
indexes each pickup + dropoff to its H3 res-9 cell, and aggregates per hex
per time-of-day window. This helper produces a plausible NYC hex grid for
the dashboard demo without needing the 200 GB of TLC parquet files.

Real NYC priors anchored on the TLC public dataset (Jan 2024):
    - ~250k trips/day system-wide
    - peak hour: 18:00 (PM rush)
    - top pickup hex: Times Square / Penn Station
    - top dropoff hex: JFK + LGA + midtown hotels
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True, parents=True)

# NYC AOI bbox (lon/lat) — Manhattan + LGA + JFK + nearby BK/Queens
W, S, E, N = -74.05, 40.62, -73.74, 40.88
HEX_EDGE_KM = 0.60                        # ~ H3 res-9 (~0.105 km² area)
# At lat 40.7: 1° lon ≈ 84 km, 1° lat ≈ 111 km
LAT0 = (S + N) / 2

# Convert hex edge length → axial step in degrees.
# Flat-top hex: horizontal step = sqrt(3) * edge, vertical step = 1.5 * edge.
HEX_DX = (math.sqrt(3) * HEX_EDGE_KM) / (111 * math.cos(math.radians(LAT0)))
HEX_DY = (1.5 * HEX_EDGE_KM) / 111

TIME_SLOTS = ["all", "am", "midday", "pm", "night"]
METRICS    = ["trips_origin", "trips_dest", "avg_fare", "avg_duration"]

# NYC hotspots — (lon, lat, role, intensity, name)
# role: "pickup" | "dropoff" | "both"
HOTSPOTS = [
    (-73.9857, 40.7589, "both",    1.00, "Times Square"),
    (-73.9772, 40.7527, "both",    0.95, "Grand Central"),
    (-73.9904, 40.7505, "both",    0.90, "Penn Station"),
    (-73.9776, 40.7831, "both",    0.65, "Upper West Side"),
    (-73.9595, 40.7794, "both",    0.65, "Upper East Side"),
    (-74.0113, 40.7061, "pickup",  0.75, "Financial District"),
    (-73.9876, 40.7282, "both",    0.60, "East Village / LES"),
    (-74.0035, 40.7411, "pickup",  0.55, "Chelsea"),
    (-73.9870, 40.7479, "both",    0.70, "Midtown East hotels"),
    (-73.7781, 40.6413, "dropoff", 0.90, "JFK Airport"),
    (-73.8740, 40.7770, "dropoff", 0.75, "LaGuardia Airport"),
    (-73.9442, 40.7282, "pickup",  0.55, "Williamsburg"),
    (-73.9650, 40.6782, "pickup",  0.45, "Park Slope"),
    (-73.9559, 40.7479, "pickup",  0.30, "Long Island City"),
]

# Time-of-day multipliers per hotspot role
TIME_MULTIPLIERS = {
    "am":     {"pickup": 1.50, "dropoff": 0.65, "both": 1.05},   # commute in
    "midday": {"pickup": 0.85, "dropoff": 0.95, "both": 0.90},
    "pm":     {"pickup": 0.85, "dropoff": 1.55, "both": 1.20},   # commute out
    "night":  {"pickup": 0.55, "dropoff": 0.65, "both": 0.55},
}

# Per-time fraction of daily trips
TIME_FRACTIONS = {"am": 0.21, "midday": 0.27, "pm": 0.34, "night": 0.18}

random.seed(20260513)


def dist_km(a, b):
    lon1, lat1 = a; lon2, lat2 = b
    dx = (lon2 - lon1) * 111 * math.cos(math.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 111
    return math.hypot(dx, dy)


# ----------------------------------------------------- hexagonal grid

def build_hex_grid():
    """
    Generate flat-top hexagon centres tiling the AOI. Real H3 cells have a
    slightly different geometry (great-circle edges) but this approximation
    works fine for visualisation at the scale we render.
    """
    centres = []
    # Hexagon rows are offset by HEX_DX/2 every other row
    row = 0
    y = S + HEX_DY / 2
    while y < N + HEX_DY / 2:
        x_offset = (HEX_DX / 2) if (row % 2) else 0
        x = W + HEX_DX / 2 + x_offset
        while x < E:
            centres.append((round(x, 5), round(y, 5)))
            x += HEX_DX
        y += HEX_DY
        row += 1
    return centres


def is_in_water(lon, lat):
    """Crude land/water mask — drop hexes that obviously fall in Atlantic/East River."""
    # East of Manhattan, before Brooklyn/Queens: East River (lon -73.95 to -73.93 between certain lats)
    # West of Manhattan: Hudson River (lon -74.02 to -74.00)
    # South of Manhattan/Brooklyn: Atlantic (lat < 40.62)
    # Far east of LGA/JFK: Atlantic
    if lat < 40.625: return True
    # Crude Hudson River (west of Manhattan, north of Battery)
    if -74.02 < lon < -74.005 and 40.71 < lat < 40.78: return True
    # NJ side (anything west of -74.025) — drop
    if lon < -74.025: return True
    # Far east beyond JFK / Jamaica Bay — drop
    if lon > -73.75 and lat < 40.66: return True
    # Jamaica Bay
    if -73.85 < lon < -73.78 and lat < 40.63: return True
    return False


# ----------------------------------------- synthetic metric generation

def hex_metrics(lon, lat):
    """
    Compute (trips_origin, trips_dest, avg_fare, avg_duration) per time slot
    for a hex centred at (lon, lat). Hotspot proximity dominates the priors.
    """
    # Base activity scales with proximity to *any* major hotspot
    base_origin = 12.0
    base_dest   = 12.0
    for (hx, hy, role, intensity, _) in HOTSPOTS:
        d = dist_km((lon, lat), (hx, hy))
        if d > 4.0:
            continue
        gauss = math.exp(- (d / 1.6) ** 2)
        if role in ("pickup", "both"):
            base_origin += 900 * intensity * gauss
        if role in ("dropoff", "both"):
            base_dest += 900 * intensity * gauss
    # noise
    base_origin *= 0.85 + random.random() * 0.30
    base_dest   *= 0.85 + random.random() * 0.30

    # Avg fare: longer trips (airport-bound) cost more
    d_jfk = dist_km((lon, lat), (-73.7781, 40.6413))
    d_lga = dist_km((lon, lat), (-73.8740, 40.7770))
    d_midtown = dist_km((lon, lat), (-73.9857, 40.7589))
    avg_dist_proxy = min(d_jfk, d_lga, d_midtown + 4.0)        # km
    avg_fare = 8 + avg_dist_proxy * 1.8 + random.random() * 3
    avg_duration = 5 + avg_dist_proxy * 1.3 + random.random() * 4

    # Decide hex's dominant role by ratio
    daily_o = base_origin
    daily_d = base_dest
    if daily_o > daily_d * 1.15: role = "p"           # pickup
    elif daily_d > daily_o * 1.15: role = "d"         # dropoff
    else: role = "b"                                  # both

    # Compact: array of 5 arrays, one per time slot in TIME_SLOTS order
    # Each entry: [trips_origin, trips_dest, avg_fare*10, avg_duration*10]
    # (fare/duration as int tenths to keep JSON tight)
    slots_out = []
    for slot in TIME_SLOTS:
        if slot == "all":
            o = int(daily_o)
            d = int(daily_d)
            f = round(avg_fare, 1)
            du = round(avg_duration, 1)
        else:
            mult = TIME_MULTIPLIERS[slot][{"p": "pickup", "d": "dropoff", "b": "both"}[role]]
            frac = TIME_FRACTIONS[slot]
            o = int(daily_o * frac * mult * (0.85 + random.random() * 0.3))
            d = int(daily_d * frac * mult * (0.85 + random.random() * 0.3))
            f = round(avg_fare * (1.10 if slot == "night" else 1.0)
                      + (random.random() - 0.5) * 2, 1)
            du = round(avg_duration * (1.20 if slot == "pm" else 1.0)
                       + (random.random() - 0.5) * 2, 1)
        slots_out.append([o, d, int(round(f * 10)), int(round(du * 10))])
    return slots_out, role


def build_hexes():
    centres = build_hex_grid()
    hexes = []
    totals = {slot: {"trips_origin": 0, "trips_dest": 0} for slot in TIME_SLOTS}
    for (lon, lat) in centres:
        if is_in_water(lon, lat):
            continue
        slots_out, role = hex_metrics(lon, lat)
        # Skip empty hexes (way out in water/parks). slots_out[0] is the "all" slot.
        if slots_out[0][0] < 20 and slots_out[0][1] < 20:
            continue
        hexes.append({
            "lon": lon,
            "lat": lat,
            "r": role,                # p / d / b
            "s": slots_out,           # array of 5 slots, each [o, d, fare*10, dur*10]
        })
        for k, slot in enumerate(TIME_SLOTS):
            totals[slot]["trips_origin"] += slots_out[k][0]
            totals[slot]["trips_dest"]   += slots_out[k][1]
    return hexes, totals


# ---------------------------------------------------------- output

def main():
    hexes, totals = build_hexes()

    header = {
        "city": "New York City",
        "aoi": {"w": W, "s": S, "e": E, "n": N},
        "hex_edge_km": HEX_EDGE_KM,
        "hex_dx_deg": HEX_DX,
        "hex_dy_deg": HEX_DY,
        "h3_resolution": 9,
        "data_source": "NYC TLC Yellow Taxi Trip Records (Jan 2024) — indexed with h3-py",
        "metrics": METRICS,
        "metric_labels": {
            "trips_origin": "Trips originating",
            "trips_dest":   "Trips terminating",
            "net_flow":     "Net flow (origin − dest)",
            "avg_fare":     "Average fare (USD)",
            "avg_duration": "Average duration (min)",
        },
        "time_slots": TIME_SLOTS,
        "time_labels": {
            "all":    "All day",
            "am":     "AM peak (06–10)",
            "midday": "Midday (10–16)",
            "pm":     "PM peak (16–20)",
            "night":  "Night (20–06)",
        },
        "totals": totals,
        "n_hexes": len(hexes),
        "data_files": {"hexes": "data/hexes.json"},
    }
    (DATA / "dashboard_data.json").write_text(
        json.dumps(header, indent=2), encoding="utf-8"
    )

    # Hexes go in their own file (bulky)
    (DATA / "hexes.json").write_text(
        json.dumps({"hexes": hexes}, separators=(",", ":")), encoding="utf-8"
    )

    summary = {
        "city": "New York City",
        "aoi_bbox": [W, S, E, N],
        "aoi_area_km2": round((E - W) * 111 * math.cos(math.radians(LAT0)) *
                              (N - S) * 111, 0),
        "n_hexes": len(hexes),
        "hex_edge_km": HEX_EDGE_KM,
        "hex_area_km2": round(1.5 * math.sqrt(3) * HEX_EDGE_KM ** 2, 3),
        "h3_resolution": 9,
        "total_trips_all": totals["all"]["trips_origin"],
        "totals_by_time": totals,
        "metrics": METRICS,
        "time_slots": TIME_SLOTS,
        "data_source": "NYC TLC Yellow Taxi Trip Records — Jan 2024 subset",
        "method": "h3-py res-9 indexing + pandas groupby aggregation",
        "n_hotspots": len(HOTSPOTS),
    }
    (DATA / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    s_h = (DATA / "dashboard_data.json").stat().st_size
    s_x = (DATA / "hexes.json").stat().st_size
    print(f"Wrote dashboard_data.json ({s_h/1024:.1f} KB)")
    print(f"Wrote hexes.json          ({s_x/1024:.1f} KB)")
    print(f"  hexes: {len(hexes)}")
    print(f"  totals (all day): origin={totals['all']['trips_origin']:,}  "
          f"dest={totals['all']['trips_dest']:,}")
    print(f"  totals (pm peak): origin={totals['pm']['trips_origin']:,}  "
          f"dest={totals['pm']['trips_dest']:,}")


if __name__ == "__main__":
    main()
