"""
Singapore Strait AIS — vessel-tracking & anchorage congestion pipeline
======================================================================

Snapshot of all AIS-reporting vessels inside the Singapore Strait AOI for
a single hour, joined to vessel-type / DWT via IMO + UNCTAD register,
binned into H3 res-8 hexes, and clustered into anchorages with DBSCAN.

Why Singapore
-------------
- One of four global maritime choke points (Suez · Hormuz · Panama · Malacca/Singapore)
- ~30% of world container volume passes through, ~84,000 vessel calls/yr
- 2024 Red Sea crisis: Asia → Europe vessels diverting via Cape of Good Hope
  pushed Singapore anchorage backlog to a record (+18% vs 2023 baseline)
- AIS coverage is dense (10+ shore receivers + Spire LEO sats), latencies < 60 s

Pipeline
--------
1. Pull 1-hour AIS snapshot for the AOI (MarineTraffic Search API or
   Spire bulk feed). Each row: MMSI, lon, lat, SOG, COG, status, timestamp.
2. Join MMSI → vessel-type / length / flag-state via IMO Vessel Index
   (we cache the join table in `data/vessel_register.parquet`).
3. Bin every vessel into an H3 res-8 hex (~460 m edge). Aggregate hex →
   {count, dominant_type}.
4. Filter status ∈ {anchored, moored}. Cluster with DBSCAN(eps≈400 m,
   min_samples=5) on the (lat, lon) projected to local UTM.
5. Match each DBSCAN cluster to an MPA-published anchorage by nearest
   centroid; emit per-anchorage roll-up {count, mean_dwell, dominant_type}.
6. Build a 12-month timeline by repeating step (1)-(5) on the 15th of
   every month and writing JSON for the dashboard.

For the public demo, `_make_dashboard_data.py` produces a procedurally
generated 1-hour snapshot at AOI scale (~950 vessels) so the dashboard
can be hosted without an AIS API key.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

W, S, E, N = 103.55, 1.05, 104.25, 1.32
H3_RES = 8         # ~460 m hex edge
DBSCAN_EPS_M = 400
DBSCAN_MIN_SAMPLES = 5


def fetch_ais_snapshot(bbox, hour_iso):
    """One-hour AIS snapshot for AOI from MarineTraffic Search API."""
    raise NotImplementedError("Elided — see notebook; uses requests + MarineTraffic token")


def load_vessel_register(mmsi_list):
    """Join MMSI → vessel_type / length_m / dwt / flag_state via IMO Vessel Index."""
    raise NotImplementedError("Elided — see notebook for IMO Vessel Index join")


def bin_to_h3(vessels, resolution: int = H3_RES):
    """Bin each vessel position to an H3 res-N hex; return {hex_id: count}."""
    import h3
    hexes = {}
    for v in vessels:
        h = h3.geo_to_h3(v["lat"], v["lon"], resolution)
        hexes[h] = hexes.get(h, 0) + 1
    return hexes


def cluster_anchorages(vessels, eps_m: float = DBSCAN_EPS_M,
                       min_samples: int = DBSCAN_MIN_SAMPLES):
    """
    DBSCAN on anchored/moored vessels.

    Project lon/lat to local UTM zone 48N for distance in metres; eps in metres.
    Returns cluster labels per vessel.
    """
    from sklearn.cluster import DBSCAN
    import pyproj
    raise NotImplementedError("Elided — see notebook for DBSCAN + UTM projection")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild-dashboard", action="store_true")
    ap.add_argument("--hour", default="2024-03-15T08:00:00+08:00")
    args = ap.parse_args()

    if args.rebuild_dashboard:
        from _make_dashboard_data import main as make_dash
        make_dash()
        return

    t0 = time.time()
    print(f"pulling AIS snapshot for {args.hour}…")
    vessels = fetch_ais_snapshot((W, S, E, N), args.hour)

    print("joining vessel register…")
    register = load_vessel_register([v["mmsi"] for v in vessels])
    for v in vessels:
        v.update(register.get(v["mmsi"], {}))

    print(f"binning to H3 res-{H3_RES}…")
    hex_density = bin_to_h3(vessels)

    print("clustering anchored vessels with DBSCAN…")
    anchored = [v for v in vessels if v.get("status") in ("anchored", "moored")]
    labels = cluster_anchorages(anchored)

    print(f"done in {time.time() - t0:.1f}s")
    from _make_dashboard_data import main as make_dash
    make_dash()


if __name__ == "__main__":
    main()
