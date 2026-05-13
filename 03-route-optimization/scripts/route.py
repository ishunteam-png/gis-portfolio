"""
Advanced Capacitated VRP with Time Windows — Tbilisi
====================================================

Solve a realistic last-mile dispatch problem:

  · 60 delivery stops sampled from real OSM POIs
  · 5 vehicles, each with capacity = 20 parcels
  · 3-min service time at each stop
  · Each stop has a 90-min time window (morning, midday, or afternoon)
  · Drivable street network with OSM maxspeed → edge travel times

Three algorithms are run and compared:

  1.  Greedy nearest-neighbour    (baseline — what naive dispatch does)
  2.  Clarke-Wright savings       (classical 1964 heuristic)
  3.  OR-Tools CVRPTW + GLS       (industry-standard solver)

Sensitivity analysis sweeps vehicle count 3→8 and plots how total cost
scales — the curve shows the marginal value of adding another vehicle.

Run
---
    PYTHONIOENCODING=utf-8 py scripts/route.py
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
DATA.mkdir(exist_ok=True)
ASSETS.mkdir(exist_ok=True)

# config
DEPOT_LATLON     = (41.6934, 44.8014)     # Freedom Square, Tbilisi
RADIUS_M         = 3000
N_STOPS          = 60
N_VEHICLES       = 5
CAPACITY         = 20
MAX_TIME_S       = 60 * 60
SERVICE_TIME_S   = 60 * 3
SEED             = 11

WINDOWS = [
    ("morning",   8 * 3600,  9 * 3600 + 30 * 60),
    ("midday",   11 * 3600, 12 * 3600 + 30 * 60),
    ("afternoon",15 * 3600, 16 * 3600 + 30 * 60),
]

DEMANDS = [(1, 0.6), (2, 0.3), (4, 0.1)]

random.seed(SEED)
np.random.seed(SEED)

COLORS = ["#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
          "#ff7f00", "#a65628", "#f781bf", "#666666"]


# 1. Network
print(f"[1/7] Pulling drive network within {RADIUS_M} m of depot ...")
G = ox.graph_from_point(DEPOT_LATLON, dist=RADIUS_M, network_type="drive",
                        simplify=True)
G = ox.routing.add_edge_speeds(G)
G = ox.routing.add_edge_travel_times(G)
# Critical: largest strongly-connected component so no unreachable cells
G = ox.truncate.largest_component(G, strongly=True)
print(f"      {G.number_of_nodes()} nodes, {G.number_of_edges()} edges (LCC)")


# 2. Sample stops
print(f"[2/7] Sampling {N_STOPS} stops from OSM POIs ...")
candidates = ox.features_from_point(
    DEPOT_LATLON,
    tags={"amenity": ["restaurant", "cafe", "fast_food", "bar", "pub"]},
    dist=RADIUS_M,
)
candidates = candidates[candidates.geometry.type == "Point"].reset_index(drop=True)
candidates = candidates.sample(n=N_STOPS, random_state=SEED).reset_index(drop=True)
candidates["stop_id"]      = range(1, len(candidates) + 1)
candidates["name"]         = candidates.get("name", "").fillna("(unnamed)")
candidates["demand"]       = np.random.choice(
    [d for d, _ in DEMANDS], size=N_STOPS, p=[p for _, p in DEMANDS])
win_choice = np.random.randint(0, len(WINDOWS), size=N_STOPS)
candidates["window_label"] = [WINDOWS[i][0] for i in win_choice]
candidates["window_open"]  = [WINDOWS[i][1] for i in win_choice]
candidates["window_close"] = [WINDOWS[i][2] for i in win_choice]
candidates[["stop_id", "name", "demand",
            "window_label", "window_open", "window_close",
            "geometry"]].to_file(DATA / "stops.geojson", driver="GeoJSON")


# 3. Snap + cost matrix
print("[3/7] Computing time matrix ...")
depot_node = ox.distance.nearest_nodes(G, DEPOT_LATLON[1], DEPOT_LATLON[0])
stop_nodes = ox.distance.nearest_nodes(
    G, candidates.geometry.x.tolist(), candidates.geometry.y.tolist()
)
all_nodes = [depot_node] + list(stop_nodes)
n = len(all_nodes)

def shortest_time(u, v):
    try:
        return int(nx.shortest_path_length(G, u, v, weight="travel_time"))
    except Exception:
        return 10_000_000

tt = np.zeros((n, n), dtype=int)
for i in range(n):
    for j in range(n):
        if i != j:
            tt[i, j] = shortest_time(all_nodes[i], all_nodes[j])

def cached_path(i, j):
    try:
        return nx.shortest_path(G, all_nodes[i], all_nodes[j], weight="travel_time")
    except Exception:
        return [all_nodes[i], all_nodes[j]]


# 4. Greedy NN
def run_greedy(n_vehicles=N_VEHICLES):
    unvisited = set(range(1, n))
    routes = [[0] for _ in range(n_vehicles)]
    rtime = [0] * n_vehicles
    rload = [0] * n_vehicles
    v = 0
    while unvisited:
        attempts = 0
        while attempts < n_vehicles:
            cur = routes[v][-1]
            feasible = [j for j in unvisited
                        if rload[v] + int(candidates["demand"][j-1]) <= CAPACITY]
            if feasible:
                nxt = min(feasible, key=lambda j: tt[cur, j])
                routes[v].append(nxt)
                rtime[v] += tt[cur, nxt] + SERVICE_TIME_S
                rload[v] += int(candidates["demand"][nxt-1])
                unvisited.discard(nxt)
                v = (v + 1) % n_vehicles
                break
            else:
                v = (v + 1) % n_vehicles
                attempts += 1
        else:
            break
    for vi in range(n_vehicles):
        rtime[vi] += tt[routes[vi][-1], 0]
        routes[vi].append(0)
    return routes, rtime


# 5. Clarke-Wright savings (1964)
def run_savings(n_vehicles=N_VEHICLES):
    pairs = []
    for i in range(1, n):
        for j in range(i + 1, n):
            s = tt[0, i] + tt[0, j] - tt[i, j]
            pairs.append((s, i, j))
    pairs.sort(reverse=True)

    route_of = {i: [0, i, 0] for i in range(1, n)}
    load_of  = {i: int(candidates["demand"][i-1]) for i in range(1, n)}
    parent   = {i: i for i in range(1, n)}

    def find(i):
        while parent[i] != i: i = parent[i]
        return i

    for s, i, j in pairs:
        ri, rj = find(i), find(j)
        if ri == rj: continue
        if load_of[ri] + load_of[rj] > CAPACITY: continue
        Ri, Rj = route_of[ri], route_of[rj]
        if Ri[-2] == i and Rj[1] == j:
            new = Ri[:-1] + Rj[1:]
        elif Rj[-2] == j and Ri[1] == i:
            new = Rj[:-1] + Ri[1:]
        else:
            continue
        route_of[ri] = new
        load_of[ri]  = load_of[ri] + load_of[rj]
        parent[rj]   = ri
        del route_of[rj]
        del load_of[rj]

    final = sorted(route_of.values(), key=len, reverse=True)
    if len(final) > n_vehicles:
        keep, tail = final[:n_vehicles], final[n_vehicles:]
        last = keep[-1]
        for r in tail:
            last = last[:-1] + r[1:]
        keep[-1] = last
        final = keep
    while len(final) < n_vehicles:
        final.append([0, 0])
    rtime = []
    for r in final:
        t = sum(tt[r[k], r[k+1]] for k in range(len(r) - 1))
        if len(r) > 2:
            t += SERVICE_TIME_S * (len(r) - 2)
        rtime.append(t)
    return final, rtime


# 6. OR-Tools CVRPTW + GLS
def run_ortools(n_vehicles=N_VEHICLES, time_limit_s=10):
    manager = pywrapcp.RoutingIndexManager(n, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def transit_cb(from_idx, to_idx):
        fi = manager.IndexToNode(from_idx); ti = manager.IndexToNode(to_idx)
        srv = SERVICE_TIME_S if fi != 0 else 0
        return int(tt[fi, ti]) + srv
    cb_t = routing.RegisterTransitCallback(transit_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(cb_t)

    # 6h slack so vehicles can wait between morning/midday/afternoon windows
    routing.AddDimension(cb_t, 6 * 3600, 24 * 3600, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for k in range(1, n):
        ot = int(candidates["window_open"][k-1])
        ct = int(candidates["window_close"][k-1])
        index = manager.NodeToIndex(k)
        time_dim.CumulVar(index).SetRange(ot, ct)
    for v in range(n_vehicles):
        time_dim.CumulVar(routing.Start(v)).SetRange(7 * 3600, 9 * 3600)

    def demand_cb(from_idx):
        node = manager.IndexToNode(from_idx)
        return 0 if node == 0 else int(candidates["demand"][node-1])
    cb_d = routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(cb_d, 0,
                                            [CAPACITY] * n_vehicles,
                                            True, "Capacity")

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = time_limit_s
    sol = routing.SolveWithParameters(params)
    assert sol is not None, "OR-Tools failed to find a feasible solution"

    routes, rtime = [], []
    for v in range(n_vehicles):
        idx = routing.Start(v); route = []
        while not routing.IsEnd(idx):
            route.append(manager.IndexToNode(idx))
            idx = sol.Value(routing.NextVar(idx))
        route.append(manager.IndexToNode(idx))
        t = sum(tt[route[k], route[k+1]] for k in range(len(route) - 1))
        if len(route) > 2:
            t += SERVICE_TIME_S * (len(route) - 2)
        routes.append(route); rtime.append(t)
    return routes, rtime


# 7. Run all + sensitivity sweep
print("[4/7] Running 3 algorithms ...")
results = {}
for name, fn in [("greedy",   run_greedy),
                 ("savings",  run_savings),
                 ("ortools",  run_ortools)]:
    t = time.time()
    routes, rtime = fn()
    print(f"      {name:>8}: total {sum(rtime)/60:6.1f} min  "
          f"max {max(rtime)/60:5.1f} min  ({time.time()-t:.1f} s)")
    results[name] = {"routes": routes, "rtime": rtime}

print("[5/7] Sensitivity sweep — vehicle count 3 to 8 ...")
sweep = []
for nv in range(3, 9):
    try:
        _, rt_g  = run_greedy(nv)
        _, rt_s  = run_savings(nv)
        _, rt_o  = run_ortools(nv, time_limit_s=5)
        sweep.append({
            "n_vehicles":   nv,
            "greedy_min":   round(sum(rt_g)/60, 1),
            "savings_min":  round(sum(rt_s)/60, 1),
            "ortools_min":  round(sum(rt_o)/60, 1),
            "ortools_max_route_min": round(max(rt_o)/60, 1),
        })
    except Exception as e:
        sweep.append({"n_vehicles": nv, "error": str(e)})

# 8. Visualise
print("[6/7] Building visualisations ...")
node_xy = {nid: (G.nodes[nid]["x"], G.nodes[nid]["y"]) for nid in G.nodes}

def routes_to_gdf(routes, label):
    feats = []
    for v, r in enumerate(routes):
        if len(r) <= 2: continue
        coords = []
        seg_time = 0
        for k in range(len(r) - 1):
            path = cached_path(r[k], r[k+1])
            coords.extend([node_xy[nd] for nd in path])
            seg_time += int(tt[r[k], r[k+1]])
        feats.append({"vehicle": v + 1, "n_stops": len(r) - 2,
                      "travel_time_min": round(seg_time / 60, 1),
                      "label": label,
                      "geometry": LineString(coords)})
    return gpd.GeoDataFrame(feats, crs="EPSG:4326")

for name, r in results.items():
    routes_to_gdf(r["routes"], name).to_file(
        DATA / f"routes_{name}.geojson", driver="GeoJSON")

# Static 3-up panel
fig, axes = plt.subplots(1, 3, figsize=(20, 7.5))
for ax, name in zip(axes, ["greedy", "savings", "ortools"]):
    gdf = routes_to_gdf(results[name]["routes"], name)
    for _, row in gdf.iterrows():
        xs, ys = zip(*row.geometry.coords)
        ax.plot(xs, ys, color=COLORS[row["vehicle"]-1], linewidth=1.8)
    ax.scatter(candidates.geometry.x, candidates.geometry.y,
               s=18, c="black", zorder=4)
    ax.scatter([DEPOT_LATLON[1]], [DEPOT_LATLON[0]],
               s=260, marker="*", c="orange", edgecolor="black", zorder=5)
    rt = results[name]["rtime"]
    ax.set_title(f"{name}  ·  total {sum(rt)/60:.1f} min  ·  max {max(rt)/60:.1f}")
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
fig.suptitle(f"Tbilisi CVRP-TW · {N_STOPS} stops, {N_VEHICLES} vehicles, cap {CAPACITY}",
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig(ASSETS / "routes_static.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# Comparison bar
fig, ax = plt.subplots(figsize=(10, 5.5))
algos = ["greedy", "savings", "ortools"]
totals  = [sum(results[a]["rtime"])/60 for a in algos]
maxes   = [max(results[a]["rtime"])/60 for a in algos]
x = np.arange(len(algos))
ax.bar(x - 0.18, totals, 0.36, label="Total time", color="#377eb8")
ax.bar(x + 0.18, maxes,  0.36, label="Longest route", color="#e41a1c")
ax.set_xticks(x); ax.set_xticklabels(algos); ax.set_ylabel("Minutes")
best = min(totals)
ax.set_title(f"Algorithm comparison — best total: {algos[totals.index(best)]} @ {best:.1f} min")
for i, (t, m) in enumerate(zip(totals, maxes)):
    ax.text(i - 0.18, t, f"{t:.0f}", ha="center", va="bottom", fontweight="bold")
    ax.text(i + 0.18, m, f"{m:.0f}", ha="center", va="bottom", fontweight="bold")
ax.legend()
plt.tight_layout()
plt.savefig(ASSETS / "comparison_chart.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# Sensitivity
fig, ax = plt.subplots(figsize=(10, 5.5))
sw_ok = [s for s in sweep if "error" not in s]
xs = [s["n_vehicles"] for s in sw_ok]
ax.plot(xs, [s["greedy_min"]  for s in sw_ok], marker="o", color="#e41a1c", label="Greedy NN")
ax.plot(xs, [s["savings_min"] for s in sw_ok], marker="s", color="#4daf4a", label="Clarke-Wright")
ax.plot(xs, [s["ortools_min"] for s in sw_ok], marker="^", color="#377eb8", label="OR-Tools (GLS)")
ax.set_xlabel("Number of vehicles")
ax.set_ylabel("Total travel + service time (min)")
ax.set_title("Sensitivity — how total cost scales with fleet size")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ASSETS / "sensitivity_chart.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# Folium combined
print("[7/7] Building Folium ...")
m = folium.Map(location=DEPOT_LATLON, zoom_start=13, tiles="cartodbpositron")
for name, dash in [("ortools", None), ("savings", "5,5"), ("greedy", "10,5")]:
    layer = folium.FeatureGroup(name=f"{name} routes",
                                show=(name == "ortools")).add_to(m)
    gdf = routes_to_gdf(results[name]["routes"], name)
    for _, r in gdf.iterrows():
        coords = [(y, x) for x, y in r.geometry.coords]
        folium.PolyLine(coords, color=COLORS[r["vehicle"]-1],
                        weight=4, opacity=0.85, dash_array=dash,
                        tooltip=(f"{name} V{r['vehicle']}  ·  "
                                 f"{r['n_stops']} stops  ·  "
                                 f"{r['travel_time_min']:.1f} min")).add_to(layer)
win_color = {"morning": "#1a9850", "midday": "#fee08b", "afternoon": "#d73027"}
for _, r in candidates.iterrows():
    folium.CircleMarker(
        [r.geometry.y, r.geometry.x], radius=5,
        color="black", weight=1,
        fill=True, fill_color=win_color[r["window_label"]], fill_opacity=0.9,
        popup=(f"<b>Stop {r['stop_id']}</b><br>{r['name']}<br>"
               f"demand: {r['demand']} parcels<br>"
               f"window: {r['window_label']}"),
    ).add_to(m)
folium.Marker(DEPOT_LATLON, icon=folium.Icon(color="orange", icon="star"),
              popup="Depot — Freedom Square").add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
m.save(ASSETS / "routes_map.html")

# Summary
summary = {
    "depot": {"lat": DEPOT_LATLON[0], "lon": DEPOT_LATLON[1]},
    "n_stops": N_STOPS, "n_vehicles": N_VEHICLES,
    "capacity_per_vehicle": CAPACITY,
    "service_time_s": SERVICE_TIME_S,
    "windows": [{"label": w[0], "open_s": w[1], "close_s": w[2]} for w in WINDOWS],
    "total_demand": int(candidates["demand"].sum()),
    "network": {"nodes": int(G.number_of_nodes()),
                "edges": int(G.number_of_edges())},
    "results": {
        a: {
            "total_min": round(sum(results[a]["rtime"]) / 60, 2),
            "max_route_min": round(max(results[a]["rtime"]) / 60, 2),
            "per_route_min": [round(t / 60, 2) for t in results[a]["rtime"]],
            "per_route_stops": [len(r) - 2 for r in results[a]["routes"]],
        }
        for a in ["greedy", "savings", "ortools"]
    },
    "improvement_ortools_vs_greedy_pct": round(
        100 * (sum(results["greedy"]["rtime"]) - sum(results["ortools"]["rtime"]))
        / sum(results["greedy"]["rtime"]), 2),
    "sensitivity_sweep": sweep,
}
(DATA / "algorithm_comparison.json").write_text(json.dumps(summary, indent=2))
(DATA / "sensitivity_sweep.json").write_text(json.dumps(sweep, indent=2))
print("All done.")
