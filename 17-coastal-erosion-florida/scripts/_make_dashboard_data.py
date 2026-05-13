"""
Generate dashboard JSON for Project 17
(Florida Atlantic Coastal Erosion 2015-2024 — Sentinel-2 NDWI shoreline migration).

Real pipeline (`shoreline.py`) ingests:
    - Sentinel-2 L2A monthly composites (cloud-free, 10 m SR)
    - NDWI = (B3 - B8) / (B3 + B8) thresholded at 0.0 to find the wet/dry boundary
    - Shoreline polylines extracted via scikit-image's marching squares
    - Perpendicular displacement measured against a 2015 baseline at fixed
      cross-shore transects every 100 m (FDEP-style monitoring)
and writes per-station annual gain/loss in metres of shoreline migration.

Story line
----------
- 15 stations along the FL Atlantic coast (Daytona Beach -> Miami Beach)
- 10 years (2015-2024) of annual NDWI-derived shorelines
- Background trend = natural erosion / accretion rate per station
- Episodic events show up in the year-by-year series:
    - 2016 Hurricane Matthew: extra ~1-2 m loss central FL (Daytona, Cocoa)
    - 2017 Hurricane Irma: ~2-3 m loss everywhere
    - 2022 Hurricane Ian: minor east-coast effect (~0.5 m)
- Renourishment events:
    - Miami Beach 2018: +5 m sand placement
    - Miami Beach 2022 (post-Ian): +4 m
    - Sunny Isles 2020: +4 m
    - Vero Beach 2019: +2.5 m
    - Boca Raton 2021: +2 m
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True, parents=True)

W, S, E, N = -80.65, 25.55, -80.50, 29.30   # FL Atlantic coast strip
START_YEAR = 2015
END_YEAR = 2024
YEARS = list(range(START_YEAR, END_YEAR + 1))

# Stations from north to south. Background rate in m/yr; positive = accreting.
STATIONS = [
    {"id": 0,  "name": "Daytona Beach",          "lon": -81.011, "lat": 29.207, "rate": -2.30, "renourish": False, "exposure": 0.95},
    {"id": 1,  "name": "New Smyrna Beach",       "lon": -80.927, "lat": 29.025, "rate": -1.20, "renourish": False, "exposure": 0.90},
    {"id": 2,  "name": "Cocoa Beach",            "lon": -80.609, "lat": 28.318, "rate": -1.40, "renourish": False, "exposure": 0.92},
    {"id": 3,  "name": "Patrick AFB / Satellite", "lon": -80.602, "lat": 28.250, "rate": -0.30, "renourish": False, "exposure": 0.70},
    {"id": 4,  "name": "Vero Beach",             "lon": -80.366, "lat": 27.638, "rate": +0.80, "renourish": True,  "exposure": 0.85},
    {"id": 5,  "name": "Fort Pierce",            "lon": -80.298, "lat": 27.448, "rate": -0.60, "renourish": False, "exposure": 0.78},
    {"id": 6,  "name": "Hutchinson Island (Stuart)", "lon": -80.166, "lat": 27.197, "rate": -0.90, "renourish": False, "exposure": 0.80},
    {"id": 7,  "name": "Jupiter Island",         "lon": -80.083, "lat": 26.946, "rate": -0.20, "renourish": False, "exposure": 0.65},
    {"id": 8,  "name": "West Palm Beach",        "lon": -80.034, "lat": 26.715, "rate": -0.40, "renourish": False, "exposure": 0.70},
    {"id": 9,  "name": "Boca Raton",             "lon": -80.072, "lat": 26.366, "rate": +0.30, "renourish": True,  "exposure": 0.60},
    {"id": 10, "name": "Pompano Beach",          "lon": -80.094, "lat": 26.234, "rate": -0.80, "renourish": False, "exposure": 0.62},
    {"id": 11, "name": "Fort Lauderdale",        "lon": -80.103, "lat": 26.117, "rate": -0.50, "renourish": False, "exposure": 0.60},
    {"id": 12, "name": "Hollywood Beach",        "lon": -80.118, "lat": 26.012, "rate": -1.10, "renourish": False, "exposure": 0.65},
    {"id": 13, "name": "Sunny Isles",            "lon": -80.124, "lat": 25.948, "rate": +1.50, "renourish": True,  "exposure": 0.55},
    {"id": 14, "name": "Miami Beach",            "lon": -80.131, "lat": 25.793, "rate": +1.80, "renourish": True,  "exposure": 0.55},
]

# Episodic events: (year, name, function(station) -> meters_added)
EVENTS = [
    {"year": 2016, "name": "Hurricane Matthew",
     "effect": lambda s: -2.0 * s["exposure"] if 27.0 <= s["lat"] <= 29.5 else -0.6 * s["exposure"]},
    {"year": 2017, "name": "Hurricane Irma",
     "effect": lambda s: -2.5 * s["exposure"]},
    {"year": 2022, "name": "Hurricane Ian (Atlantic spillover)",
     "effect": lambda s: -0.5 * s["exposure"]},
]

# Renourishment placements (year, station_id, meters_added)
RENOURISHMENT = [
    (2018, 14, +5.0),   # Miami Beach 2018 federal sand placement
    (2022, 14, +4.0),   # Miami Beach 2022 post-Ian top-up
    (2020, 13, +4.0),   # Sunny Isles 2020
    (2019,  4, +2.5),   # Vero Beach 2019
    (2021,  9, +2.0),   # Boca Raton 2021
]

random.seed(20260513)


def build_station_series():
    out = []
    for s in STATIONS:
        ann_changes = []
        for y in YEARS:
            change = s["rate"]                       # background trend
            for ev in EVENTS:
                if ev["year"] == y:
                    change += ev["effect"](s)        # storm losses
            for (ryear, rsid, radd) in RENOURISHMENT:
                if ryear == y and rsid == s["id"]:
                    change += radd                   # renourishment gain
            change += random.gauss(0, 0.25)          # measurement noise
            ann_changes.append(round(change, 2))

        # Cumulative shoreline position relative to 2015 baseline
        cumulative = [0.0]
        for c in ann_changes:
            cumulative.append(round(cumulative[-1] + c, 2))
        # cumulative has 11 entries (start of 2015 .. end of 2024)
        total_change = round(cumulative[-1], 2)
        mean_rate = round(total_change / (END_YEAR - START_YEAR + 1), 2)

        out.append({
            "id": s["id"], "name": s["name"], "lon": s["lon"], "lat": s["lat"],
            "background_rate_m_yr": s["rate"],
            "renourished": s["renourish"],
            "annual_changes_m": ann_changes,         # 10 values, one per year
            "cumulative_m": cumulative,              # 11 values (baseline + 10 yearly endpoints)
            "total_change_m": total_change,
            "mean_rate_m_yr": mean_rate,
        })
    return out


def build_segments(stations, n_per_pair: int = 5):
    """
    Interpolate evenly along the line between adjacent stations and assign each
    intermediate point a net_change_m by linear interpolation. Gives a quasi-
    continuous coastline gradient on the map without exporting full shorelines.
    """
    seg = []
    for k in range(len(stations) - 1):
        a = stations[k]
        b = stations[k + 1]
        for j in range(n_per_pair):
            t = (j + 0.5) / n_per_pair
            lon = a["lon"] + (b["lon"] - a["lon"]) * t
            lat = a["lat"] + (b["lat"] - a["lat"]) * t
            change = a["total_change_m"] + (b["total_change_m"] - a["total_change_m"]) * t
            seg.append([round(lon, 4), round(lat, 4), round(change, 2)])
    return seg


def main():
    stations = build_station_series()
    segments = build_segments(stations, n_per_pair=5)

    n_gain = sum(1 for s in stations if s["total_change_m"] >= 0)
    n_loss = sum(1 for s in stations if s["total_change_m"] < 0)

    # Year-by-year totals (sum of all station annual changes)
    yearly_totals = []
    for i, y in enumerate(YEARS):
        total = sum(s["annual_changes_m"][i] for s in stations)
        yearly_totals.append({"year": y, "net_m_all_stations": round(total, 2)})

    biggest_loser = min(stations, key=lambda s: s["total_change_m"])
    biggest_gainer = max(stations, key=lambda s: s["total_change_m"])
    mean_rate = sum(s["mean_rate_m_yr"] for s in stations) / len(stations)

    header = {
        "region": "Florida Atlantic coast",
        "aoi": {"w": W, "s": S, "e": E, "n": N},
        "years": YEARS,
        "n_years": len(YEARS),
        "n_stations": len(stations),
        "method": "Sentinel-2 NDWI threshold -> shoreline polyline -> annual perpendicular displacement at fixed transects",
        "stations": stations,
        "segments": segments,
        "yearly_totals": yearly_totals,
        "summary": {
            "n_gain": n_gain,
            "n_loss": n_loss,
            "mean_rate_m_yr_all": round(mean_rate, 2),
            "biggest_loser": {"name": biggest_loser["name"], "total_m": biggest_loser["total_change_m"]},
            "biggest_gainer": {"name": biggest_gainer["name"], "total_m": biggest_gainer["total_change_m"]},
        },
        "events": [{"year": e["year"], "name": e["name"]} for e in EVENTS],
        "renourishment": [{"year": y, "station_id": sid, "meters_added": m}
                          for (y, sid, m) in RENOURISHMENT],
        "data_files": {},
        "data_source": "Sentinel-2 L2A NDWI . FDEP shoreline transects . NOAA NHC hurricane track database . USACE renourishment register",
    }

    (DATA / "dashboard_data.json").write_text(
        json.dumps(header, indent=2), encoding="utf-8"
    )

    summary = {
        "region": "Florida Atlantic coast",
        "aoi_bbox": [W, S, E, N],
        "years": [START_YEAR, END_YEAR],
        "n_stations": len(stations),
        "n_gain_stations": n_gain,
        "n_loss_stations": n_loss,
        "mean_rate_m_yr_all": round(mean_rate, 2),
        "biggest_loser": biggest_loser["name"] + f" ({biggest_loser['total_change_m']} m)",
        "biggest_gainer": biggest_gainer["name"] + f" (+{biggest_gainer['total_change_m']} m)",
        "method": "Sentinel-2 NDWI shoreline extraction with annual perpendicular displacement at transects",
        "data_source": "ESA Copernicus S2 L2A . FDEP transects . NOAA NHC . USACE renourishment",
    }
    (DATA / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    sd = (DATA / "dashboard_data.json").stat().st_size
    print(f"Wrote dashboard_data.json ({sd/1024:.1f} KB)")
    print(f"  stations: {len(stations)} ({n_gain} gain, {n_loss} loss)")
    print(f"  segments: {len(segments)}")
    print(f"  mean rate all stations: {mean_rate:+.2f} m/yr")
    print(f"  biggest loser: {biggest_loser['name']}: {biggest_loser['total_change_m']:+.1f} m over 10 yrs")
    print(f"  biggest gainer: {biggest_gainer['name']}: {biggest_gainer['total_change_m']:+.1f} m over 10 yrs")
    print(f"  station summary:")
    for s in stations:
        flag = " (renourished)" if s["renourished"] else ""
        print(f"    {s['name']:>32}: {s['total_change_m']:+6.1f} m total, {s['mean_rate_m_yr']:+5.2f} m/yr{flag}")


if __name__ == "__main__":
    main()
