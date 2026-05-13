"""
Jakarta Compound Flood Risk — Multi-Factor Hazard + Exposure Model
==================================================================

Jakarta is widely considered the most flood-prone megacity on Earth:
 · 40 % of the city sits below sea level
 · land subsides ~10 cm/yr in the north (and >25 cm/yr at the worst spots)
 · 13 rivers cross the city before discharging into the Java Sea
 · monsoon rainfall + tidal flooding interact to produce compound floods
 · the consequence is so severe that Indonesia is moving its capital to
   Nusantara (Borneo) to escape it

This script builds a screening-grade flood-risk map for central Jakarta
combining FOUR terrain-and-landuse signals:

    1. HAND  (Height Above Nearest Drainage)            — fluvial proxy
    2. Slope (degrees, from DEM gradient)                — ponding proxy
    3. Drainage density (m of waterway per km^2 cell)    — capacity proxy
    4. Imperviousness (% sealed-surface land use)        — runoff proxy

These four are weighted into a composite risk index (0-1), then pixels
are classified into 4 risk bands (low / moderate / high / very high).
Buildings AND critical infrastructure are tagged with their risk band
so exposure can be counted per asset class.

Run:
    PYTHONIOENCODING=utf-8 py scripts/flood.py
"""

from __future__ import annotations

import json
import time
import urllib.request
from math import asinh, floor, pi, tan
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
import rasterio
from matplotlib import colors as mcolors
from rasterio.features import rasterize
from rasterio.merge import merge as rio_merge
from rasterio.warp import (Resampling, calculate_default_transform, reproject,
                           transform_bounds)
from scipy import ndimage
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
DATA.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

# Central Jakarta DKI core
AOI_LATLON_BBOX = (-6.30, 106.74, -6.06, 106.95)
ZOOM = 12
TILE_URL = ("https://elevation-tiles-prod.s3.amazonaws.com/"
            "geotiff/{z}/{x}/{y}.tif")

WEIGHTS = {"hand": 0.40, "slope": 0.25,
           "impervious": 0.20, "drainage_density": 0.15}

RISK_LABELS = ["low", "moderate", "high", "very high"]
RISK_COLORS = ["#2c7fb8", "#ffeda0", "#fd8d3c", "#bd0026"]

IMPERVIOUS_TAGS = {"landuse": ["residential", "commercial", "industrial",
                                "retail", "construction", "garages"]}
PERVIOUS_TAGS   = {"landuse": ["forest", "meadow", "grass", "farmland",
                                "cemetery", "allotments", "village_green"],
                   "leisure": ["park", "garden", "nature_reserve",
                                "pitch", "playground", "common"],
                   "natural": ["wood", "water", "wetland", "scrub"]}

CRITICAL_TAGS = {
    "amenity": ["hospital", "clinic", "school", "kindergarten", "university",
                "college", "fire_station", "police", "townhall"],
    "emergency": True,
}


# 1. Fetch + mosaic DEM
t0 = time.time()
print(f"[1/8] Fetching Mapzen terrain tiles @ z={ZOOM} for Jakarta AOI ...")

def deg2tile(lat, lon, z):
    n = 2 ** z
    x = floor((lon + 180.0) / 360.0 * n)
    y = floor((1.0 - asinh(tan(lat * pi / 180.0)) / pi) / 2.0 * n)
    return x, y

south, west, north, east = AOI_LATLON_BBOX
x_min, y_min = deg2tile(north, west, ZOOM)
x_max, y_max = deg2tile(south, east, ZOOM)
tiles = [(x, y) for x in range(x_min, x_max + 1)
                  for y in range(y_min, y_max + 1)]

tile_paths = []
for x, y in tiles:
    p = DATA / f"tile_{ZOOM}_{x}_{y}.tif"
    if not p.exists():
        urllib.request.urlretrieve(TILE_URL.format(z=ZOOM, x=x, y=y), p)
    tile_paths.append(p)
srcs = [rasterio.open(p) for p in tile_paths]
mosaic, mosaic_transform = rio_merge(srcs)
profile = srcs[0].profile.copy()
crs = srcs[0].crs
for s in srcs: s.close()
profile.update(driver="GTiff", height=mosaic.shape[1], width=mosaic.shape[2],
               transform=mosaic_transform, count=1, dtype=mosaic.dtype,
               compress="lzw")
dem_path = DATA / "dem.tif"
with rasterio.open(dem_path, "w", **profile) as dst:
    dst.write(mosaic[0], 1)

aoi_3857 = transform_bounds("EPSG:4326", crs, west, south, east, north, densify_pts=21)
with rasterio.open(dem_path) as src:
    window = rasterio.windows.from_bounds(*aoi_3857, transform=src.transform)
    window = window.round_offsets().round_lengths()
    dem = src.read(1, window=window).astype("float32")
    dem_transform = src.window_transform(window)
    dem_profile = src.profile.copy()
    dem_profile.update(height=dem.shape[0], width=dem.shape[1],
                       transform=dem_transform, dtype="float32",
                       nodata=None, compress="lzw")
H, W = dem.shape
px_m = abs(dem_transform.a) / np.cos(np.deg2rad((south + north) / 2))


# 2. Pull OSM layers
print("[2/8] Pulling OSM layers ...")
aoi_poly = box(west, south, east, north)

def safe_features(tags, label):
    try:
        gdf = ox.features_from_polygon(aoi_poly, tags=tags)
        print(f"      {label}: {len(gdf)} features")
        return gdf
    except Exception as e:
        print(f"      {label}: FAILED ({e})")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

waterways   = safe_features({"waterway": ["river", "stream", "canal",
                                          "drain", "ditch"]},        "waterways")
buildings   = safe_features({"building": True},                       "buildings")
impervious  = safe_features(IMPERVIOUS_TAGS,                          "impervious LU")
pervious    = safe_features(PERVIOUS_TAGS,                            "pervious LU")
critical    = safe_features(CRITICAL_TAGS,                            "critical infra")

buildings = buildings[buildings.geometry.type.isin(["Polygon", "MultiPolygon"])].reset_index(drop=True)
critical = critical[critical.geometry.type.isin(["Point", "Polygon", "MultiPolygon"])].reset_index(drop=True)


# 3. Rasterise
print("[3/8] Rasterising layers ...")
def rasterise_to_dem(gdf, value=1, dtype="uint8"):
    if gdf is None or gdf.empty:
        return np.zeros((H, W), dtype=dtype)
    gp = gdf.to_crs(crs)
    geoms = ((g, value) for g in gp.geometry if g is not None and not g.is_empty)
    return rasterize(geoms, out_shape=(H, W), transform=dem_transform,
                     fill=0, dtype=dtype)

water_mask      = rasterise_to_dem(waterways)
impervious_mask = rasterise_to_dem(impervious)
pervious_mask   = rasterise_to_dem(pervious)


# 4. Hazard factors
print("[4/8] Computing HAND, slope, drainage density, imperviousness ...")
_, (ny, nx) = ndimage.distance_transform_edt(water_mask == 0, return_indices=True)
hand = (dem - dem[ny, nx]).astype("float32")
hand = np.where(water_mask == 1, 0.0, hand)

gy, gx = np.gradient(dem)
slope = np.degrees(np.arctan(np.hypot(gy, gx) / px_m)).astype("float32")

KERNEL_RADIUS_M = 500
kr = max(int(KERNEL_RADIUS_M / px_m), 3)
yy, xx = np.ogrid[-kr:kr+1, -kr:kr+1]
kernel = (xx*xx + yy*yy <= kr*kr).astype("float32")
water_count = ndimage.convolve(water_mask.astype("float32"), kernel, mode="constant")
kernel_area_m2 = kernel.sum() * (px_m ** 2)
drainage_density = (water_count * px_m) / (kernel_area_m2 / 1e6)
drainage_density = drainage_density.astype("float32")

imp_count = ndimage.convolve(impervious_mask.astype("float32"), kernel, mode="constant")
prv_count = ndimage.convolve(pervious_mask.astype("float32"),   kernel, mode="constant")
denom = imp_count + prv_count
impervious_frac = np.where(denom > 0, imp_count / denom, 0.0).astype("float32")


# 5. Composite risk
print("[5/8] Building composite risk index ...")
def normalise(a, lo=None, hi=None, invert=False, clip=True):
    a = a.astype("float32")
    if lo is None: lo = np.nanpercentile(a, 2)
    if hi is None: hi = np.nanpercentile(a, 98)
    if hi - lo < 1e-9: return np.zeros_like(a)
    out = (a - lo) / (hi - lo)
    if clip: out = np.clip(out, 0.0, 1.0)
    return 1.0 - out if invert else out

hand_n     = normalise(np.where(hand >= 0, hand, np.nan), lo=0, hi=15,  invert=True)
slope_n    = normalise(slope,                              lo=0, hi=8,   invert=True)
imperv_n   = normalise(impervious_frac,                    lo=0, hi=1.0, invert=False)
drain_n    = normalise(drainage_density,                   lo=0, hi=2000, invert=True)

risk_index = (WEIGHTS["hand"]             * hand_n
              + WEIGHTS["slope"]          * slope_n
              + WEIGHTS["impervious"]     * imperv_n
              + WEIGHTS["drainage_density"] * drain_n).astype("float32")
risk_index = np.nan_to_num(risk_index, nan=0.0)

qs = np.quantile(risk_index, [0.25, 0.55, 0.80])
risk_band = np.full(risk_index.shape, 1, dtype="uint8")
risk_band[risk_index > qs[0]] = 2
risk_band[risk_index > qs[1]] = 3
risk_band[risk_index > qs[2]] = 4
band_counts = {RISK_LABELS[i-1]: int((risk_band == i).sum())
               for i in range(1, 5)}

for name, arr in [("hand", hand), ("slope", slope),
                  ("drainage_density", drainage_density),
                  ("impervious_frac", impervious_frac),
                  ("risk_index", risk_index)]:
    with rasterio.open(DATA / f"{name}.tif", "w", **dem_profile) as dst:
        dst.write(arr, 1)
band_prof = dem_profile.copy(); band_prof.update(dtype="uint8", nodata=None)
with rasterio.open(DATA / "risk_band.tif", "w", **band_prof) as dst:
    dst.write(risk_band, 1)


# 6. Asset exposure
print("[6/8] Tagging assets with risk band ...")
inv = ~dem_transform

def sample_risk(gdf):
    if gdf.empty:
        return np.array([]), np.array([])
    centroids = gdf.geometry.to_crs(crs).centroid
    rows = np.empty(len(centroids), dtype=int)
    cols = np.empty(len(centroids), dtype=int)
    for k, p in enumerate(centroids):
        c, r = inv * (p.x, p.y)
        cols[k], rows[k] = int(c), int(r)
    valid = (rows >= 0) & (rows < H) & (cols >= 0) & (cols < W)
    band = np.full(len(centroids), 0, dtype=int)
    risk = np.full(len(centroids), np.nan, dtype="float32")
    band[valid] = risk_band[rows[valid], cols[valid]]
    risk[valid] = risk_index[rows[valid], cols[valid]]
    return band, risk

b_band, b_risk = sample_risk(buildings)
buildings["risk_band"]  = b_band
buildings["risk_idx"]   = b_risk
buildings["risk_label"] = ["unknown" if b == 0 else RISK_LABELS[b-1] for b in b_band]

c_band, c_risk = sample_risk(critical)
critical["risk_band"]  = c_band
critical["risk_idx"]   = c_risk
critical["risk_label"] = ["unknown" if b == 0 else RISK_LABELS[b-1] for b in c_band]

def best_type(row):
    for col in ("amenity", "emergency", "healthcare", "office"):
        if col in row.index and isinstance(row[col], str) and row[col]:
            return row[col]
    return "other"
critical["type"] = critical.apply(best_type, axis=1)

b_cols = ["geometry", "risk_band", "risk_idx", "risk_label"]
if "building" in buildings.columns:
    b_cols.insert(1, "building")
buildings[b_cols].to_file(DATA / "buildings_risk.geojson", driver="GeoJSON")

c_cols = ["geometry", "type", "risk_band", "risk_idx", "risk_label"]
if "name" in critical.columns:
    c_cols.insert(2, "name")
critical[c_cols].to_file(DATA / "critical_infra_risk.geojson", driver="GeoJSON")

exposure = {
    "buildings": {RISK_LABELS[i-1]: int((buildings["risk_band"] == i).sum())
                  for i in range(1, 5)},
    "buildings_unknown": int((buildings["risk_band"] == 0).sum()),
    "critical": {RISK_LABELS[i-1]: int((critical["risk_band"] == i).sum())
                 for i in range(1, 5)},
    "critical_unknown": int((critical["risk_band"] == 0).sum()),
    "critical_by_type_high": (
        critical[critical["risk_band"] >= 3]
        .groupby("type").size().to_dict()
    ),
}


# 7. Visualise
print("[7/8] Rendering figures ...")
ext = (dem_transform.c, dem_transform.c + W * dem_transform.a,
       dem_transform.f + H * dem_transform.e, dem_transform.f)

risk_cmap = mcolors.ListedColormap(RISK_COLORS)
risk_norm = mcolors.BoundaryNorm([0.5, 1.5, 2.5, 3.5, 4.5], risk_cmap.N)

fig, axes = plt.subplots(2, 2, figsize=(15, 13))
im = axes[0, 0].imshow(risk_band, cmap=risk_cmap, norm=risk_norm,
                       extent=ext, origin="upper")
cb = plt.colorbar(im, ax=axes[0, 0], ticks=[1, 2, 3, 4], shrink=0.6)
cb.ax.set_yticklabels(RISK_LABELS)
axes[0, 0].set_title("Composite flood risk band", fontsize=11)

im = axes[0, 1].imshow(np.clip(hand, 0, 30), cmap="viridis_r",
                       extent=ext, origin="upper")
plt.colorbar(im, ax=axes[0, 1], shrink=0.6, label="m above drainage")
axes[0, 1].set_title("HAND — Height Above Nearest Drainage", fontsize=11)

im = axes[1, 0].imshow(impervious_frac, cmap="Reds",
                       extent=ext, origin="upper")
plt.colorbar(im, ax=axes[1, 0], shrink=0.6, label="impervious fraction (0-1)")
axes[1, 0].set_title("Imperviousness (impervious LU / total LU within 500 m)",
                     fontsize=11)

im = axes[1, 1].imshow(drainage_density, cmap="Blues",
                       extent=ext, origin="upper")
plt.colorbar(im, ax=axes[1, 1], shrink=0.6, label="m of waterway per km^2")
axes[1, 1].set_title("Drainage density (sparse = high risk)", fontsize=11)

for ax in axes.flat:
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle(f"Jakarta — Compound flood-risk model · DEM: AWS Terrain Tiles z={ZOOM}",
             fontsize=13, y=0.995)
plt.tight_layout()
plt.savefig(ASSETS / "flood_hero.png", dpi=130, bbox_inches="tight")
plt.close(fig)

# Components
fig, axes = plt.subplots(2, 2, figsize=(14, 13))
for ax, (arr, title, cmap) in zip(axes.flat, [
    (hand_n,   "HAND (normalised, inverted)",          "YlOrRd"),
    (slope_n,  "Slope (normalised, inverted)",         "YlOrRd"),
    (imperv_n, "Imperviousness (normalised)",          "YlOrRd"),
    (drain_n,  "Drainage density (normalised, inverted)", "YlOrRd"),
]):
    im = ax.imshow(arr, cmap=cmap, vmin=0, vmax=1, extent=ext, origin="upper")
    plt.colorbar(im, ax=ax, shrink=0.6, label="risk contribution 0-1")
    ax.set_title(title, fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
fig.suptitle("Risk components", fontsize=13, y=0.995)
plt.tight_layout()
plt.savefig(ASSETS / "risk_components.png", dpi=130, bbox_inches="tight")
plt.close(fig)

# Building exposure
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.bar(RISK_LABELS,
       [exposure["buildings"][l] for l in RISK_LABELS],
       color=RISK_COLORS, edgecolor="black", linewidth=0.4)
for i, lbl in enumerate(RISK_LABELS):
    n = exposure["buildings"][lbl]
    ax.text(i, n, f"{n:,}", ha="center", va="bottom", fontweight="bold")
ax.set_ylabel("Buildings in this risk band")
ax.set_title(f"Building exposure by composite risk band")
plt.tight_layout()
plt.savefig(ASSETS / "exposure_by_band.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# Critical infra
ct = (critical.groupby(["type", "risk_label"]).size()
              .unstack(fill_value=0).reindex(columns=RISK_LABELS, fill_value=0))
ct["_high"] = ct.get("high", 0) + ct.get("very high", 0)
ct = ct.sort_values("_high", ascending=False).head(10).drop(columns="_high")

fig, ax = plt.subplots(figsize=(10.5, 6))
bottoms = np.zeros(len(ct), dtype=int)
for label, color in zip(RISK_LABELS, RISK_COLORS):
    vals = ct[label].values
    ax.bar(ct.index, vals, bottom=bottoms, color=color, edgecolor="black",
           linewidth=0.3, label=label)
    bottoms += vals
ax.set_ylabel("Number of critical-infra assets")
ax.set_title("Critical infrastructure exposure per asset type (top 10 by high+very-high)")
ax.legend(title="Risk band", loc="upper right")
plt.xticks(rotation=22, ha="right")
plt.tight_layout()
plt.savefig(ASSETS / "critical_infra_chart.png", dpi=150, bbox_inches="tight")
plt.close(fig)


# 8. Folium interactive map
print("[8/8] Building Folium interactive map ...")

dst_crs = "EPSG:4326"
src_bounds = rasterio.transform.array_bounds(H, W, dem_transform)
dst_tf, dst_w, dst_h = calculate_default_transform(crs, dst_crs, W, H, *src_bounds)
band_4326 = np.zeros((dst_h, dst_w), dtype="uint8")
reproject(risk_band, band_4326, src_transform=dem_transform, src_crs=crs,
          dst_transform=dst_tf, dst_crs=dst_crs, resampling=Resampling.nearest)
rgba = np.zeros((dst_h, dst_w, 4), dtype="uint8")
for i, hexcol in enumerate(RISK_COLORS, start=1):
    rgb = tuple(int(hexcol[j:j+2], 16) for j in (1, 3, 5))
    rgba[band_4326 == i] = list(rgb) + [180]
overlay_path = ASSETS / "_risk_band_overlay.png"
plt.imsave(overlay_path, rgba)

lt = dst_tf.f
lb = lt + dst_h * dst_tf.e
ll = dst_tf.c
lr = ll + dst_w * dst_tf.a

m = folium.Map(location=[(south + north) / 2, (west + east) / 2],
               zoom_start=12, tiles="cartodbpositron")
folium.raster_layers.ImageOverlay(
    image=str(overlay_path),
    bounds=[[lb, ll], [lt, lr]],
    opacity=0.65, name="Composite risk band",
).add_to(m)

exposed = critical[critical["risk_band"] >= 3].copy()
exposed_4326 = exposed.to_crs(4326)
exposed_4326["lat"] = exposed_4326.geometry.centroid.y
exposed_4326["lon"] = exposed_4326.geometry.centroid.x
infra_layer = folium.FeatureGroup(
    name=f"Exposed critical infra (high+VH, n={len(exposed)})"
).add_to(m)
for _, r in exposed_4326.iterrows():
    nm = r.get("name", "")
    if not isinstance(nm, str): nm = ""
    color = "#bd0026" if r["risk_band"] == 4 else "#fd8d3c"
    folium.CircleMarker(
        [r["lat"], r["lon"]], radius=6, color="#222", weight=1,
        fill=True, fill_color=color, fill_opacity=0.9,
        popup=folium.Popup(
            f"<b>{r['type']}</b>"
            + (f" — {nm}" if nm else "")
            + f"<br>risk band: {r['risk_label']}"
            + f"<br>risk idx: {r['risk_idx']:.2f}",
            max_width=280),
    ).add_to(infra_layer)

folium.LayerControl(collapsed=False).add_to(m)
m.save(ASSETS / "flood_map.html")


# Summary
summary = {
    "city":         "Jakarta, Indonesia",
    "aoi_bbox_latlon": {"south": south, "west": west, "north": north, "east": east},
    "dem": {
        "source": "AWS Terrain Tiles (Mapzen)",
        "zoom":   ZOOM,
        "shape":  list(dem.shape),
        "px_metres_approx": round(float(px_m), 1),
        "elev_min_max_mean": [float(dem.min()), float(dem.max()), float(dem.mean())],
    },
    "weights": WEIGHTS,
    "feature_counts": {
        "waterways":  int(len(waterways)),
        "buildings":  int(len(buildings)),
        "impervious_lu": int(len(impervious)),
        "pervious_lu":   int(len(pervious)),
        "critical_infra": int(len(critical)),
    },
    "band_pixel_counts": band_counts,
    "exposure": exposure,
    "runtime_seconds": round(time.time() - t0, 1),
}
(DATA / "run_summary.json").write_text(json.dumps(summary, indent=2))
print(f"Done in {summary['runtime_seconds']} s.")
