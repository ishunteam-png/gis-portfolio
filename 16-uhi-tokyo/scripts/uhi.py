"""
Tokyo Urban Heat Island — Landsat 8/9 thermal LST + Sentinel-2 NDVI
====================================================================

Per-cell land surface temperature (LST) and NDVI for the August 2024
heat wave peak over a 50 km×50 km AOI centred on Tokyo Station, on a
32×32 grid (~1.5 km cells).

Why Tokyo
---------
- 37 M people, world's largest metro area
- Tropical August (mean Tmax 31°C), 2024 was JMA's hottest summer on record
- Strong urban/rural gradient (Yamanote loop core → Tama suburbs → Okutama
  forest) and large internal cooling features (Imperial Palace, Yoyogi,
  Ueno) make the "more trees = cooler block" story visible at one scale.

Pipeline
--------
1. Pull a cloud-free Landsat-9 path 107 row 035 scene for early August
   (USGS EarthExplorer Collection 2 Level-2). Use the surface-temperature
   band ST_B10 (already atmospherically corrected by USGS).
2. Pull the same-week Sentinel-2 L2A cloud-free composite via STAC
   (Element84 Earth Search). Compute NDVI = (B8 - B4) / (B8 + B4).
3. Resample both to a 32×32 (~1.5 km) grid covering the AOI; take the
   per-cell mean (or median, robust to scan-line glitches).
4. Pull JAXA AW3D30 DEM, average per cell — used to drop high-elevation
   cells from the "rural baseline" calculation (Mt Takao is ~600 m,
   inherently cooler than sea-level Saitama).
5. Compute UHI intensity:
       UHI = mean(LST | dist_to_center < 5 km) -
             mean(LST | dist_to_center > 20 km AND elevation < 100 m)
6. Compute Spearman ρ(LST, NDVI) globally and land-only (water cells
   decouple — they're cool but bare).
7. Write per-cell JSON for the dashboard.

For the public demo, `_make_dashboard_data.py` produces a procedural
1024-cell snapshot anchored on Tokyo's known cool/hot features. The real
pipeline above swaps the procedural step for STAC pulls + rasterio
resampling.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

W, S, E, N = 139.467, 35.430, 140.067, 35.930
GRID_N = 32
SNAPSHOT_DATE = "2024-08-12"


def fetch_landsat_lst(bbox, date):
    """USGS Collection 2 Level-2 LST (ST_B10) for the cloud-free overpass."""
    import pystac_client
    raise NotImplementedError("Elided — see notebook; use Landsatlook / pystac-client")


def fetch_sentinel2_ndvi(bbox, date_window):
    """Sentinel-2 L2A monthly composite NDVI via Element84 STAC."""
    raise NotImplementedError("Elided — see notebook; pystac + stackstac")


def resample_to_grid(raster, bbox, grid_n: int):
    """Resample a single-band raster to grid_n × grid_n cell means."""
    import rasterio
    from rasterio.warp import reproject, Resampling
    raise NotImplementedError("Elided — see notebook for rasterio warp")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-dashboard", action="store_true")
    ap.add_argument("--date", default=SNAPSHOT_DATE)
    args = ap.parse_args()

    if args.rebuild_dashboard:
        from _make_dashboard_data import main as make_dash
        make_dash()
        return

    t0 = time.time()
    print(f"pulling Landsat 9 LST for {args.date}…")
    lst_raster = fetch_landsat_lst((W, S, E, N), args.date)

    print("pulling Sentinel-2 NDVI composite…")
    ndvi_raster = fetch_sentinel2_ndvi((W, S, E, N), (args.date, args.date))

    print(f"resampling to {GRID_N}×{GRID_N}…")
    lst_grid = resample_to_grid(lst_raster, (W, S, E, N), GRID_N)
    ndvi_grid = resample_to_grid(ndvi_raster, (W, S, E, N), GRID_N)

    print(f"done in {time.time() - t0:.1f}s")
    from _make_dashboard_data import main as make_dash
    make_dash()


if __name__ == "__main__":
    main()
