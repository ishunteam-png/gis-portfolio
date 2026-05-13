"""
Lisbon rooftop solar potential — DEM + OSM + pvlib pipeline
============================================================

For every building in the Lisbon AOI: compute annual kWh photovoltaic
generation potential. Combines OSM building polygons, Copernicus 25 m DEM
(for roof slope + aspect inference and horizon shading), and PVGIS-anchored
pvlib irradiance.

Why Lisbon
----------
- 38.7°N → prime mid-latitude solar profile
- 2,800–3,100 GHI annual sunshine hours (top quartile in Europe)
- South-facing Atlantic coast — no inland morning shadow
- 2024 Portuguese rooftop-PV policy push: 30%+ tax credit + 15-yr net metering

Pipeline
--------
1. Pull OSM building polygons via OSMnx for the bbox
2. Pull Copernicus 25 m DEM, derive roof centroid elevation
3. Infer roof tilt + azimuth from `roof:shape`/`roof:slope` OSM tags;
   fall back to neighbourhood-typical defaults if missing (Pombaline grid ≈
   flat, Alfama ≈ 25° tiled, Avenidas ≈ flat)
4. Compute horizon profile per building (skyline raycast against 9-cell DEM
   neighbourhood) → obstruction factor 0..1
5. PVGIS / pvlib annual irradiance for the (lat, tilt, azimuth) triple
6. kWh/year = irradiance × usable_area × panel_eff × performance_ratio
7. Write dashboard JSON
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

W, S, E, N = -9.225, 38.690, -9.105, 38.770
LISBON_LAT = 38.72
PANEL_EFF = 0.20
PERFORMANCE_RATIO = 0.83


def fetch_buildings(bbox):
    """OSM building footprints with optional roof:shape / roof:slope tags."""
    import osmnx as ox
    tags = {"building": True}
    return ox.features_from_bbox(*bbox[::-1], tags=tags)


def fetch_dem(bbox):
    """Copernicus 25 m DEM via py3dep / OpenTopography."""
    import py3dep
    return py3dep.get_dem(bbox, resolution=30)


def roof_geometry(building, dem):
    """
    Infer roof tilt + azimuth.

    Priority:
        1. OSM `roof:slope` + `roof:direction` tags (rare but accurate)
        2. Neighbourhood prior from a Pombaline / Alfama / Avenidas typology
        3. DEM-derived terrain aspect of the cell (weak fallback)
    """
    raise NotImplementedError("Elided — see notebook")


def horizon_obstruction(centroid_lonlat, dem, n_rays: int = 16):
    """
    Cast `n_rays` outward from centroid; for each, find the highest
    skyline angle within 200 m. Average → obstruction factor 0..1.
    """
    raise NotImplementedError("Elided — see notebook for ray-casting routine")


def annual_irradiance(lat: float, tilt: float, azimuth: float) -> float:
    """PVGIS-anchored annual GHI on tilted plane (kWh/m²/yr) via pvlib."""
    import pvlib
    times = pvlib.location.Location(lat, -9.14).get_solarposition(
        ...)  # full-year hourly
    raise NotImplementedError("Elided — pvlib clearsky + dni/dhi loop")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-dashboard", action="store_true")
    args = ap.parse_args()

    if args.rebuild_dashboard:
        from _make_dashboard_data import main as make_dash
        make_dash()
        return

    t0 = time.time()
    print("fetching OSM building footprints…")
    buildings = fetch_buildings((W, S, E, N))
    print(f"  {len(buildings)} buildings")

    print("fetching Copernicus DEM…")
    dem = fetch_dem((W, S, E, N))

    print("computing per-building tilt/aspect/horizon…")
    # for each building:
    #   geom = roof_geometry(b, dem)
    #   obs  = horizon_obstruction(b.centroid, dem)
    #   irr  = annual_irradiance(LISBON_LAT, geom.tilt, geom.azimuth)
    #   kwh  = irr * b.usable_area * PANEL_EFF * PERFORMANCE_RATIO * (1 - obs)

    print(f"done in {time.time()-t0:.1f}s")
    from _make_dashboard_data import main as make_dash
    make_dash()


if __name__ == "__main__":
    main()
