"""
Florida Atlantic Coastal Erosion 2015-2024
===========================================

Annual shoreline migration from Sentinel-2 NDWI composites along the
Florida Atlantic coast (Daytona Beach -> Miami Beach), measured at 15
named monitoring stations as perpendicular displacement against the
2015 baseline shoreline.

Why this AOI
------------
- One of the most studied erosion fronts on Earth (FDEP runs ~120 fixed
  transects from Nassau County to Miami-Dade)
- Mixed natural / engineered behaviour - natural erosion in the north,
  renourishment-dominated accretion in Miami-Dade
- High-energy hurricane belt (Atlantic basin) - 2016 Matthew, 2017 Irma
  and 2022 Ian all show up as discrete year-on-year jumps
- Sentinel-2 has 10 m optical, 5-day revisit, cloud-free composites work
  well at this latitude

Pipeline
--------
1. For each year 2015-2024, pull a Sentinel-2 L2A cloud-free monthly
   composite for the spring-tide low-water window (typically February).
   Use Element84 STAC + stackstac for the mosaic.
2. Compute NDWI = (B3 - B8) / (B3 + B8). Threshold at 0.0 to separate
   wet (water) from dry (sand/vegetation).
3. Extract the shoreline polyline with scikit-image's marching squares
   on the binary NDWI mask. Smooth with a 5-pixel running median to
   suppress salt-and-pepper noise.
4. At each FDEP transect (every 100 m), measure the perpendicular
   displacement (m) of the year-N shoreline against the 2015 baseline.
5. Roll up to 15 named "stations" by averaging the 5-20 transects within
   each station's 1 km perimeter.
6. Stamp episodic events (hurricane tracks from NOAA NHC) and
   renourishment placements (USACE register) onto the year-by-year
   series for the dashboard.

For the public demo, `_make_dashboard_data.py` produces a procedural
15-station time series anchored on the real FDEP background rates and
the known hurricane / renourishment timeline.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

W, S, E, N = -80.65, 25.55, -80.50, 29.30
YEARS = list(range(2015, 2025))
NDWI_THRESHOLD = 0.0
TRANSECT_SPACING_M = 100


def fetch_sentinel2_annual(bbox, year, month_window=(1, 3)):
    """Sentinel-2 L2A cloud-free composite for a given year/window."""
    import pystac_client
    raise NotImplementedError("Elided — see notebook; pystac + stackstac")


def ndwi(arr_green, arr_nir):
    """NDWI = (Green - NIR) / (Green + NIR)."""
    return (arr_green - arr_nir) / (arr_green + arr_nir + 1e-12)


def extract_shoreline(ndwi_arr, threshold: float = NDWI_THRESHOLD):
    """Marching-squares contour at NDWI = threshold."""
    from skimage import measure
    raise NotImplementedError("Elided — see notebook for skimage.measure.find_contours")


def measure_displacement(baseline_polyline, year_polyline, transect_spacing_m: float = TRANSECT_SPACING_M):
    """
    Perpendicular displacement at fixed transects along the baseline.

    Returns a list of (lon, lat, displacement_m) tuples.
    """
    raise NotImplementedError("Elided — see notebook for shapely cross-shore projection")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-dashboard", action="store_true")
    args = ap.parse_args()

    if args.rebuild_dashboard:
        from _make_dashboard_data import main as make_dash
        make_dash()
        return

    t0 = time.time()
    baseline = None
    yearly_displacement = {}

    for y in YEARS:
        print(f"  fetching Sentinel-2 composite for {y}…")
        green, nir = fetch_sentinel2_annual((W, S, E, N), y)
        ndwi_arr = ndwi(green, nir)
        shoreline = extract_shoreline(ndwi_arr)
        if baseline is None:
            baseline = shoreline                # 2015 baseline
        yearly_displacement[y] = measure_displacement(baseline, shoreline)

    print(f"done in {time.time() - t0:.1f}s")
    from _make_dashboard_data import main as make_dash
    make_dash()


if __name__ == "__main__":
    main()
