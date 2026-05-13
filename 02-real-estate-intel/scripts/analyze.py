"""
Café Suitability — multi-factor spatial-MCDA over any OSM-mapped city
=====================================================================

Score every grid cell in a city on "good place to open a café" using FIVE
signals derived purely from OpenStreetMap + the street network:

    +  Foot traffic      (shops + transit POI density)
    +  Residential       (residential building density)
    +  Tourist           (attractions + hotels + museums)
    +  Walkability       (street-intersection density in walk network)
    -  Competition       (existing café density)

The composite score is normalised to 0–1 and the 20 highest-scoring cells
are surfaced. The script accepts any OSM-mapped city via --city and ships
with a built-in 3-city comparison mode that runs Tbilisi / Yerevan / Sofia
side-by-side. It can also validate the model against the *existing*
distribution of cafés in the city (Spearman rank correlation between cell
score and observed café density — the model is "honest" if it gives high
scores to areas that already have many cafés).

Run
---
    py scripts/analyze.py                       # default: Tbilisi
    py scripts/analyze.py --city "Yerevan, Armenia"
    py scripts/analyze.py --compare             # Tbilisi + Yerevan + Sofia
    py scripts/analyze.py --validate            # adds correlation panel
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox
from scipy.stats import spearmanr
from shapely.geometry import box

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"

CELL_SIZE_M = 250
RADII = {"foot_traffic": 300, "competition": 200, "residential": 300,
         "tourist": 500, "walkability": 400}
WEIGHTS = {"foot_traffic": 0.30, "residential": 0.20, "tourist": 0.15,
           "walkability": 0.20, "competition": 0.15}

COMPARE_CITIES = [
    "Tbilisi, Georgia",
    "Yerevan, Armenia",
    "Sofia, Bulgaria",
]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def pick_utm_epsg(lon: float, lat: float) -> int:
    """Auto-pick the right UTM zone for a lat/lon (so distances are in metres)."""
    zone = int((lon + 180) / 6) + 1
    return 32600 + zone if lat >= 0 else 32700 + zone


def safe_features(poly, tags, label):
    try:
        gdf = ox.features_from_polygon(poly, tags=tags)
        print(f"      {label:<22} {len(gdf):>6}")
        return gdf
    except Exception as e:
        print(f"      {label:<22} FAILED ({e})")
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")


def to_centroids_utm(gdf, utm_epsg):
    if gdf is None or gdf.empty:
        return gpd.GeoDataFrame(geometry=[], crs=f"EPSG:{utm_epsg}")
    out = gdf.to_crs(utm_epsg).copy()
    out["geometry"] = out.geometry.centroid
    return out[["geometry"]]


def normalize(s):
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else s * 0.0


def analyse_city(place: str, do_validate: bool) -> dict:
    """Full single-city pipeline. Returns summary dict."""
    print(f"\n=== {place} ===")
    t0 = time.time()
    slug = slugify(place)
    out_data = DATA / slug; out_data.mkdir(parents=True, exist_ok=True)
    out_assets = ASSETS / slug; out_assets.mkdir(parents=True, exist_ok=True)

    print(f"[1/7] Fetching boundary ...")
    city = ox.geocode_to_gdf(place)
    boundary = city.geometry.iloc[0]
    centroid = boundary.centroid
    utm_epsg = pick_utm_epsg(centroid.x, centroid.y)
    city_u = city.to_crs(utm_epsg)
    area_km2 = float(city_u.area.iloc[0] / 1e6)
    print(f"      area {area_km2:.1f} km^2, utm epsg {utm_epsg}")

    print(f"[2/7] Pulling OSM POIs ...")
    cafes       = safe_features(boundary, {"amenity": "cafe"}, "cafes")
    shops       = safe_features(boundary, {"shop": True}, "shops")
    transit     = safe_features(boundary, {"highway": "bus_stop",
                                            "railway": "station",
                                            "public_transport": "platform"}, "transit")
    tourist     = safe_features(boundary, {"tourism": ["attraction", "hotel",
                                                       "museum", "viewpoint",
                                                       "gallery"]}, "tourist")
    residential = safe_features(boundary, {"building": ["residential",
                                                         "apartments", "house",
                                                         "detached",
                                                         "semidetached_house"]},
                                "residential")

    print(f"[3/7] Pulling walk network for intersection density ...")
    try:
        G = ox.graph_from_polygon(boundary, network_type="walk", simplify=True)
        intersections = [(d["x"], d["y"]) for n, d in G.nodes(data=True)
                         if G.degree(n) >= 3]
        ints_gdf = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([x for x, _ in intersections],
                                        [y for _, y in intersections]),
            crs="EPSG:4326",
        )
        ints_u = to_centroids_utm(ints_gdf, utm_epsg)
        print(f"      walk graph: {G.number_of_nodes()} nodes, "
              f"{len(intersections)} intersection nodes")
    except Exception as e:
        print(f"      walk network FAILED ({e}); walkability will be zero")
        ints_u = gpd.GeoDataFrame(geometry=[], crs=f"EPSG:{utm_epsg}")

    cafes_u, shops_u, transit_u, tourist_u, res_u = [
        to_centroids_utm(g, utm_epsg)
        for g in (cafes, shops, transit, tourist, residential)
    ]

    print(f"[4/7] Building {CELL_SIZE_M} m grid ...")
    minx, miny, maxx, maxy = city_u.total_bounds
    xs = np.arange(minx, maxx, CELL_SIZE_M)
    ys = np.arange(miny, maxy, CELL_SIZE_M)
    cells = [box(x, y, x + CELL_SIZE_M, y + CELL_SIZE_M) for x in xs for y in ys]
    grid_raw = gpd.GeoDataFrame({"cell_id": range(len(cells))},
                                geometry=cells, crs=f"EPSG:{utm_epsg}")
    grid = gpd.overlay(grid_raw, city_u[["geometry"]],
                       how="intersection").reset_index(drop=True)
    print(f"      {len(grid)} cells inside boundary")

    print(f"[5/7] Computing density features ...")
    grid["centroid"] = grid.geometry.centroid

    def count_within(points, radius):
        if points.empty:
            return np.zeros(len(grid), dtype=int)
        buf = grid.set_geometry(grid.centroid.buffer(radius))[["cell_id",
                                                                "geometry"]]
        j = gpd.sjoin(points, buf, predicate="within", how="inner")
        c = j.groupby("cell_id").size()
        return grid["cell_id"].map(c).fillna(0).astype(int).values

    grid["n_shops"]       = count_within(shops_u,   RADII["foot_traffic"])
    grid["n_transit"]     = count_within(transit_u, RADII["foot_traffic"])
    grid["n_cafes"]       = count_within(cafes_u,   RADII["competition"])
    grid["n_residential"] = count_within(res_u,     RADII["residential"])
    grid["n_tourist"]     = count_within(tourist_u, RADII["tourist"])
    grid["n_intersect"]   = count_within(ints_u,    RADII["walkability"])

    grid["foot_traffic"] = grid["n_shops"] + grid["n_transit"]
    grid["competition"]  = grid["n_cafes"]
    grid["residential"]  = grid["n_residential"]
    grid["tourist"]      = grid["n_tourist"]
    grid["walkability"]  = grid["n_intersect"]

    for col in ["foot_traffic", "competition", "residential",
                "tourist", "walkability"]:
        grid[f"{col}_n"] = normalize(grid[col])

    grid["suitability_raw"] = (
        WEIGHTS["foot_traffic"] * grid["foot_traffic_n"]
        + WEIGHTS["residential"] * grid["residential_n"]
        + WEIGHTS["tourist"]     * grid["tourist_n"]
        + WEIGHTS["walkability"] * grid["walkability_n"]
        - WEIGHTS["competition"] * grid["competition_n"]
    )
    grid["suitability"] = normalize(grid["suitability_raw"])

    print(f"[6/7] Visualising + exporting ...")
    grid_wgs = grid.drop(columns=["centroid"]).to_crs(4326)
    top20 = grid_wgs.nlargest(20, "suitability").copy()
    top20["rank"] = range(1, len(top20) + 1)
    grid_wgs.to_file(out_data / "grid_scores.geojson", driver="GeoJSON")
    top20.to_file(out_data / "top20_candidates.geojson", driver="GeoJSON")

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    panels = [
        ("foot_traffic", "Foot traffic (shops + transit, 300 m)",  "YlOrRd"),
        ("residential",  "Residential density (300 m)",            "Greens"),
        ("tourist",      "Tourist amenities (500 m)",              "Purples"),
        ("walkability",  "Walkability — intersections (400 m)",    "Oranges"),
        ("competition",  "Competing cafés (200 m, penalty)",       "Blues"),
        ("suitability",  "Composite suitability",                   "RdYlGn"),
    ]
    for ax, (col, title, cmap) in zip(axes.flat, panels):
        grid_wgs.plot(column=col, ax=ax, cmap=cmap, legend=True,
                      legend_kwds={"shrink": 0.55}, edgecolor="none")
        ax.set_title(title, fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    top20.plot(ax=axes[1, 2], facecolor="none", edgecolor="black", linewidth=1.5)
    fig.suptitle(f"{place} — café suitability score components",
                 fontsize=13, y=0.995)
    plt.tight_layout()
    plt.savefig(out_assets / "score_components.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 9))
    grid_wgs.plot(column="walkability", ax=ax, cmap="Oranges", legend=True,
                  legend_kwds={"shrink": 0.6, "label": "intersections (400 m)"},
                  edgecolor="none")
    ax.set_title(f"{place} — walkability proxy (intersection density)", fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout()
    plt.savefig(out_assets / "walkability_panel.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 11))
    grid_wgs.plot(column="suitability", ax=ax, cmap="RdYlGn", legend=True,
                  legend_kwds={"shrink": 0.6, "label": "Suitability (0–1)"},
                  edgecolor="none")
    top20.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=1.8)
    for _, r in top20.iterrows():
        c = r.geometry.centroid
        ax.annotate(str(r["rank"]), xy=(c.x, c.y), ha="center", va="center",
                    fontsize=7, fontweight="bold", color="black")
    ax.set_title(f"{place} — best 250 m cells for a new café", fontsize=13, pad=12)
    ax.set_xticks([]); ax.set_yticks([])
    plt.tight_layout()
    plt.savefig(out_assets / "suitability_hero.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"      building Folium ...")
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=12,
                   tiles="cartodbpositron")
    folium.Choropleth(
        geo_data=json.loads(grid_wgs.to_json()),
        data=grid_wgs, columns=["cell_id", "suitability"],
        key_on="feature.properties.cell_id",
        fill_color="RdYlGn", fill_opacity=0.6, line_opacity=0.05,
        legend_name="Café suitability (0–1)",
    ).add_to(m)
    grp = folium.FeatureGroup(name="Top 20").add_to(m)
    for _, r in top20.iterrows():
        c = r.geometry.centroid
        folium.CircleMarker(
            [c.y, c.x], radius=7, color="black", weight=2,
            fill=True, fill_color="yellow", fill_opacity=0.9,
            popup=folium.Popup(
                f"<b>Rank #{r['rank']}</b><br>"
                f"score: {r['suitability']:.3f}<br>"
                f"foot: {int(r['foot_traffic'])} POIs · "
                f"walk: {int(r['walkability'])} intersections<br>"
                f"res: {int(r['residential'])} · "
                f"tour: {int(r['tourist'])} · "
                f"comp: {int(r['competition'])} cafés",
                max_width=300),
        ).add_to(grp)
    folium.LayerControl().add_to(m)
    m.save(out_assets / "suitability_map.html")

    spearman_rho = None
    if do_validate:
        print(f"[7/7] Validating against existing café distribution ...")
        rho, pval = spearmanr(grid["suitability"], grid["n_cafes"])
        spearman_rho = float(rho)
        print(f"      Spearman rho(suitability, n_cafes) = {rho:.3f}  (p={pval:.2e})")
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(grid["suitability"], grid["n_cafes"], s=4, alpha=0.4,
                   color="#1f77b4")
        ax.set_xlabel("Model suitability score")
        ax.set_ylabel("Observed cafés in cell (200 m)")
        ax.set_title(f"{place} — validation\nSpearman ρ = {rho:.3f} "
                     f"(higher = model agrees with reality)")
        plt.tight_layout()
        plt.savefig(out_assets / "validation.png", dpi=140, bbox_inches="tight")
        plt.close(fig)

    summary = {
        "place": place,
        "area_km2": round(area_km2, 1),
        "utm_epsg": utm_epsg,
        "cell_size_m": CELL_SIZE_M,
        "radii_m": RADII,
        "weights": WEIGHTS,
        "n_cells": int(len(grid)),
        "feature_counts": {
            "cafes": int(len(cafes)), "shops": int(len(shops)),
            "transit": int(len(transit)), "tourist": int(len(tourist)),
            "residential": int(len(residential)),
            "walk_intersections": int(len(ints_u)),
        },
        "suitability_stats": {
            "min":    float(grid["suitability"].min()),
            "max":    float(grid["suitability"].max()),
            "mean":   float(grid["suitability"].mean()),
            "median": float(grid["suitability"].median()),
        },
        "top5": [
            {
                "rank":  int(r["rank"]),
                "score": float(r["suitability"]),
                "foot_traffic": int(r["foot_traffic"]),
                "residential": int(r["residential"]),
                "tourist":     int(r["tourist"]),
                "walkability": int(r["walkability"]),
                "competition": int(r["competition"]),
                "lon": float(r.geometry.centroid.x),
                "lat": float(r.geometry.centroid.y),
            }
            for _, r in top20.head(5).iterrows()
        ],
        "validation_spearman": spearman_rho,
        "runtime_seconds": round(time.time() - t0, 1),
    }
    (out_data / "run_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--city", default="Tbilisi, Georgia",
                   help="OSM-recognised place name")
    p.add_argument("--compare", action="store_true",
                   help="Run 3-city comparison (Tbilisi, Yerevan, Sofia)")
    p.add_argument("--validate", action="store_true",
                   help="Compute Spearman correlation vs existing café density")
    args = p.parse_args()

    cities = COMPARE_CITIES if args.compare else [args.city]
    summaries = [analyse_city(c, args.validate) for c in cities]

    if args.compare:
        print("\n=== Comparison ===")
        fig, axes = plt.subplots(1, 3, figsize=(20, 7))
        for ax, s in zip(axes, summaries):
            slug = slugify(s["place"])
            grid_wgs = gpd.read_file(DATA / slug / "grid_scores.geojson")
            top20 = gpd.read_file(DATA / slug / "top20_candidates.geojson")
            grid_wgs.plot(column="suitability", ax=ax, cmap="RdYlGn",
                          legend=False, edgecolor="none")
            top20.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=1.2)
            ax.set_title(f"{s['place']}\n"
                         f"area {s['area_km2']:.0f} km^2 · "
                         f"{s['n_cells']:,} cells · "
                         f"{s['feature_counts']['cafes']} cafés · "
                         f"ρ={s['validation_spearman'] if s['validation_spearman'] else '—'}",
                         fontsize=11)
            ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle("Café suitability — multi-city comparison",
                     fontsize=14, y=1.02)
        plt.tight_layout()
        plt.savefig(ASSETS / "comparison.png", dpi=140, bbox_inches="tight")
        plt.close(fig)


if __name__ == "__main__":
    main()
