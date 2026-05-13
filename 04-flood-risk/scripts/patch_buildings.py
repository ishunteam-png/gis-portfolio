"""
Patch script — Jakarta has too many OSM buildings to pull in one Overpass
query, so the main pipeline fetched 0. This script pulls them in 6 chunks
(2 x 3 grid over the AOI), spatial-joins to the existing risk_band raster,
writes buildings_risk.geojson, and re-renders the exposure chart.
"""
from __future__ import annotations
import json
import time
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
import pandas as pd
import rasterio
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"

AOI = (-6.30, 106.74, -6.06, 106.95)   # south, west, north, east
RISK_LABELS = ["low", "moderate", "high", "very high"]
RISK_COLORS = ["#2c7fb8", "#ffeda0", "#fd8d3c", "#bd0026"]

print("[1/4] Loading existing risk_band.tif ...")
with rasterio.open(DATA / "risk_band.tif") as src:
    risk_band = src.read(1)
    crs = src.crs
    transform = src.transform
    H, W = src.shape
inv = ~transform

print(f"      raster shape {risk_band.shape}, crs {crs}")

print("[2/4] Pulling buildings in 6 chunks (2 cols x 3 rows) ...")
s, w, n, e = AOI
n_cols, n_rows = 2, 3
lon_edges = np.linspace(w, e, n_cols + 1)
lat_edges = np.linspace(s, n, n_rows + 1)

t0 = time.time()
chunks = []
for r in range(n_rows):
    for c in range(n_cols):
        ww, ee = lon_edges[c], lon_edges[c+1]
        ss, nn = lat_edges[r], lat_edges[r+1]
        poly = box(ww, ss, ee, nn)
        try:
            gdf = ox.features_from_polygon(poly, tags={"building": True})
            gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]
            print(f"      chunk r{r}c{c}: {len(gdf):>7} buildings")
            chunks.append(gdf)
        except Exception as err:
            print(f"      chunk r{r}c{c}: FAILED ({type(err).__name__}: {err})")
buildings = pd.concat(chunks, ignore_index=True) if chunks else gpd.GeoDataFrame()
buildings = gpd.GeoDataFrame(buildings, geometry="geometry", crs="EPSG:4326")
print(f"      total buildings: {len(buildings):,}  (fetched in {time.time()-t0:.0f} s)")

print("[3/4] Sampling risk band at each building centroid ...")
centroids = buildings.geometry.to_crs(crs).centroid
rows = np.empty(len(centroids), dtype=int)
cols = np.empty(len(centroids), dtype=int)
for k, p in enumerate(centroids):
    cc, rr = inv * (p.x, p.y)
    cols[k], rows[k] = int(cc), int(rr)
valid = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W)
b_band = np.zeros(len(centroids), dtype=int)
b_band[valid] = risk_band[rows[valid], cols[valid]]
buildings["risk_band"] = b_band
buildings["risk_label"] = ["unknown" if b == 0 else RISK_LABELS[b-1] for b in b_band]

exposure = {
    RISK_LABELS[i-1]: int((buildings["risk_band"] == i).sum())
    for i in range(1, 5)
}
exposure["unknown"] = int((buildings["risk_band"] == 0).sum())
print(f"      buildings per band: {exposure}")

print("[4/4] Saving GeoJSON + re-rendering exposure chart ...")
keep = ["geometry", "risk_band", "risk_label"]
if "building" in buildings.columns: keep.insert(1, "building")
buildings[keep].to_file(DATA / "buildings_risk.geojson", driver="GeoJSON")

fig, ax = plt.subplots(figsize=(9, 5.5))
ax.bar(RISK_LABELS,
       [exposure[l] for l in RISK_LABELS],
       color=RISK_COLORS, edgecolor="black", linewidth=0.4)
for i, lbl in enumerate(RISK_LABELS):
    n = exposure[lbl]
    ax.text(i, n, f"{n:,}", ha="center", va="bottom", fontweight="bold", fontsize=11)
ax.set_ylabel("Buildings in this risk band")
total = sum(exposure[l] for l in RISK_LABELS) + exposure["unknown"]
ax.set_title(f"Jakarta building exposure by composite flood-risk band  ·  AOI total = {total:,} buildings (OSM)")
plt.tight_layout()
plt.savefig(ASSETS / "exposure_by_band.png", dpi=150, bbox_inches="tight")
plt.close(fig)

summary = json.loads((DATA / "run_summary.json").read_text())
summary["feature_counts"]["buildings"] = int(len(buildings))
summary["exposure"]["buildings"] = {l: exposure[l] for l in RISK_LABELS}
summary["exposure"]["buildings_unknown"] = exposure["unknown"]
(DATA / "run_summary.json").write_text(json.dumps(summary, indent=2))
print(f"      total = {total:,}; high+VH = {exposure['high'] + exposure['very high']:,}")
