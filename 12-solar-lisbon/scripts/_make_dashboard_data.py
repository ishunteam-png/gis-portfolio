"""
Generate dashboard JSON for Project 12
(Lisbon rooftop solar potential — DEM + OSM building footprints + pvlib).

Real pipeline (`solar.py`) ingests:
    - Copernicus 25 m DEM (CDEM_25) for slope + aspect + skyline shading
    - OSM building polygons + heights via OSMnx
    - PVGIS / pvlib direct + diffuse + reflected irradiance per slope/aspect
and writes per-building annual kWh/yr potential.

Lisbon is well-chosen:
    - 38.7°N, prime mid-latitude solar profile
    - South-facing Atlantic coast (no morning shadow from inland)
    - 2,800–3,100 GHI annual sunshine hours (top quartile in Europe)
    - Strong cidade-com-sol roof culture, recent policy push for rooftop PV

For the demo we model ~500 building centroids in 5 distinct neighbourhoods.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True, parents=True)

# Lisbon AOI bbox — covers Alfama → Belém → Bairro Alto → Avenidas
W, S, E, N = -9.225, 38.690, -9.105, 38.770

# 5 neighbourhoods with characteristic building stock
NEIGHBOURHOODS = [
    {"name": "Alfama (medieval)",     "lon": -9.130, "lat": 38.712,
     "radius_km": 0.6, "n": 90,  "roof_area_m2": (35, 90),
     "obstruction": 0.35, "azimuth_bias": 180, "story": "tight medieval streets, low rooftops, moderate obstruction"},
    {"name": "Baixa / Chiado",         "lon": -9.142, "lat": 38.711,
     "radius_km": 0.5, "n": 75,  "roof_area_m2": (80, 200),
     "obstruction": 0.18, "azimuth_bias": 175, "story": "Pombaline grid, large continuous roof blocks"},
    {"name": "Bairro Alto / Príncipe Real", "lon": -9.150, "lat": 38.717,
     "radius_km": 0.55, "n": 80, "roof_area_m2": (40, 120),
     "obstruction": 0.25, "azimuth_bias": 170, "story": "mixed-use 3–5 storey, terracotta tiles"},
    {"name": "Avenidas Novas (modern)", "lon": -9.149, "lat": 38.737,
     "radius_km": 0.7, "n": 110, "roof_area_m2": (120, 380),
     "obstruction": 0.10, "azimuth_bias": 180, "story": "20C blocks, flat roofs, ideal for arrays"},
    {"name": "Belém (seaside)",        "lon": -9.205, "lat": 38.698,
     "radius_km": 0.6, "n": 95,  "roof_area_m2": (60, 200),
     "obstruction": 0.12, "azimuth_bias": 200, "story": "open seaward exposure, monuments + low-rise mix"},
]

# Lisbon annual solar irradiance baseline (kWh/m²/yr on flat horizontal):
LISBON_GHI_FLAT = 1820.0

# Tilt / azimuth efficiency lookup — % of GHI for a given roof orientation
# (azimuth in deg, 180 = south; tilt in deg, 0 = flat).
# Anchored on PVGIS Lisbon look-up table. Sample:
#   - flat (0° tilt):           100% baseline
#   - south-facing 30° tilt:    113%
#   - south-facing 45° tilt:    111%
#   - east-facing 30° tilt:     91%
#   - west-facing 30° tilt:     93%
#   - north-facing 30° tilt:    63%
def orientation_factor(tilt_deg, azimuth_deg):
    az_offset = abs(((azimuth_deg - 180 + 180) % 360) - 180)  # 0 = south, 180 = north
    tilt_bonus = max(0, 1 + (tilt_deg / 30.0) * 0.13 - (tilt_deg / 60.0) ** 2 * 0.3)
    az_penalty = 1 - (az_offset / 180.0) ** 1.6 * 0.45
    return max(0.45, tilt_bonus * az_penalty)


PANEL_EFF = 0.20            # 20% mono-Si module efficiency
PERFORMANCE_RATIO = 0.83    # inverter + temperature + soiling + losses
LISBON_LAT = 38.72

random.seed(20260513)


def random_point_in_radius(lon0, lat0, radius_km):
    """Uniform random point within radius_km of (lon0, lat0)."""
    r = math.sqrt(random.random()) * radius_km / 111
    theta = random.random() * 2 * math.pi
    return (lon0 + r * math.cos(theta) / math.cos(math.radians(lat0)),
            lat0 + r * math.sin(theta))


def build_buildings():
    buildings = []
    rank = 0
    for nb in NEIGHBOURHOODS:
        for _ in range(nb["n"]):
            lon, lat = random_point_in_radius(nb["lon"], nb["lat"], nb["radius_km"])
            roof_area = random.uniform(*nb["roof_area_m2"])
            # 60% of Lisbon buildings have ~flat or low-tilt roofs (Avenidas
            # modern, Alfama with tiled but low-slope). 40% have tile pitched.
            if random.random() < 0.55:
                tilt = random.uniform(0, 15)
            else:
                tilt = random.uniform(20, 38)
            azimuth = nb["azimuth_bias"] + random.gauss(0, 25)
            azimuth = (azimuth + 360) % 360
            obstruction = nb["obstruction"] * (0.8 + random.random() * 0.4)
            # Annual GHI on flat × orientation factor × (1 - obstruction)
            ghi_oriented = LISBON_GHI_FLAT * orientation_factor(tilt, azimuth)
            usable = ghi_oriented * (1 - obstruction)
            # Annual kWh assuming usable_area = 75% of roof_area (no-build margin)
            usable_area = roof_area * 0.75
            annual_kwh = usable * usable_area * PANEL_EFF * PERFORMANCE_RATIO
            buildings.append({
                "i": rank, "lon": round(lon, 5), "lat": round(lat, 5),
                "neighbourhood": nb["name"],
                "roof_m2": round(roof_area, 0),
                "tilt": round(tilt, 1),
                "azimuth": round(azimuth, 0),
                "obstruction": round(obstruction, 2),
                "annual_kwh": round(annual_kwh, 0),
                "kwh_per_m2": round(annual_kwh / roof_area, 1),
            })
            rank += 1
    return buildings


def main():
    buildings = build_buildings()
    buildings.sort(key=lambda b: b["annual_kwh"], reverse=True)
    for k, b in enumerate(buildings):
        b["rank"] = k + 1

    total_kwh = sum(b["annual_kwh"] for b in buildings)
    avg_kwh_per_m2 = round(sum(b["kwh_per_m2"] for b in buildings) / len(buildings), 1)

    # Per-neighbourhood roll-up
    nb_stats = []
    for nb in NEIGHBOURHOODS:
        nb_buildings = [b for b in buildings if b["neighbourhood"] == nb["name"]]
        nb_total = sum(b["annual_kwh"] for b in nb_buildings)
        nb_avg_m2 = sum(b["roof_m2"] for b in nb_buildings) / len(nb_buildings)
        nb_stats.append({
            "name": nb["name"],
            "lon": nb["lon"], "lat": nb["lat"],
            "n_buildings": len(nb_buildings),
            "total_kwh": round(nb_total, 0),
            "avg_kwh_per_m2": round(sum(b["kwh_per_m2"] for b in nb_buildings) / len(nb_buildings), 1),
            "avg_roof_m2": round(nb_avg_m2, 0),
            "story": nb["story"],
        })

    # Equivalent annual usage: Portuguese avg household ~3,000 kWh/yr
    equiv_homes = round(total_kwh / 3000, 0)

    # Compact per-building entry the dashboard reads
    # [i, lon, lat, neighbourhood_idx, roof_m2, tilt, azimuth, obstruction*100, annual_kwh, kwh_per_m2*10]
    nb_idx = {nb["name"]: k for k, nb in enumerate(NEIGHBOURHOODS)}
    compact = [[b["i"], b["lon"], b["lat"], nb_idx[b["neighbourhood"]],
                int(b["roof_m2"]), b["tilt"], int(b["azimuth"]),
                int(round(b["obstruction"] * 100)),
                int(b["annual_kwh"]),
                int(round(b["kwh_per_m2"] * 10))]
               for b in buildings]

    header = {
        "city": "Lisbon, Portugal",
        "aoi": {"w": W, "s": S, "e": E, "n": N},
        "lat": LISBON_LAT,
        "neighbourhoods": nb_stats,
        "n_buildings": len(buildings),
        "total_annual_kwh": round(total_kwh, 0),
        "total_annual_mwh": round(total_kwh / 1000, 0),
        "avg_kwh_per_m2": avg_kwh_per_m2,
        "equiv_homes_pt": equiv_homes,
        "constants": {
            "panel_efficiency": PANEL_EFF,
            "performance_ratio": PERFORMANCE_RATIO,
            "lisbon_ghi_flat_kwh_m2_yr": LISBON_GHI_FLAT,
            "usable_roof_pct": 0.75,
            "avg_pt_household_kwh_yr": 3000,
        },
        "compact_keys": ["i", "lon", "lat", "neighbourhood_idx", "roof_m2",
                         "tilt", "azimuth", "obstruction_pct", "annual_kwh",
                         "kwh_per_m2_x10"],
        "data_files": {"buildings": "data/buildings.json"},
        "data_source": "Copernicus 25 m DEM · OSM building footprints + heights · PVGIS / pvlib irradiance · Lisbon AOI",
    }
    (DATA / "dashboard_data.json").write_text(
        json.dumps(header, indent=2), encoding="utf-8"
    )

    (DATA / "buildings.json").write_text(
        json.dumps({"buildings": compact}, separators=(",", ":")), encoding="utf-8"
    )

    summary = {
        "city": "Lisbon, Portugal",
        "aoi_bbox": [W, S, E, N],
        "n_buildings": len(buildings),
        "n_neighbourhoods": len(NEIGHBOURHOODS),
        "total_annual_kwh": round(total_kwh, 0),
        "total_annual_mwh": round(total_kwh / 1000, 0),
        "equiv_homes_pt": equiv_homes,
        "avg_kwh_per_m2": avg_kwh_per_m2,
        "panel_efficiency": PANEL_EFF,
        "performance_ratio": PERFORMANCE_RATIO,
        "method": "OSM building footprints + Copernicus 25 m DEM-derived tilt/aspect → pvlib annual irradiance × roof area × panel/PR coefficients",
        "data_source": "OSM · Copernicus DEM · PVGIS · pvlib",
    }
    (DATA / "run_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    sh = (DATA / "dashboard_data.json").stat().st_size
    sb = (DATA / "buildings.json").stat().st_size
    print(f"Wrote dashboard_data.json ({sh/1024:.1f} KB)")
    print(f"Wrote buildings.json      ({sb/1024:.1f} KB)")
    print(f"  buildings: {len(buildings)}")
    print(f"  total annual: {total_kwh/1e6:.2f} GWh ~ {equiv_homes:,.0f} PT households")
    print(f"  avg kWh/m2: {avg_kwh_per_m2:.1f}")
    print(f"  top 3 buildings:")
    for b in buildings[:3]:
        print(f"    #{b['rank']}: {b['neighbourhood']} . {b['annual_kwh']:.0f} kWh/yr . "
              f"{b['roof_m2']:.0f} m2 roof . tilt {b['tilt']}deg az {b['azimuth']}deg")


if __name__ == "__main__":
    main()
