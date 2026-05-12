# Project 3 — Advanced Capacitated VRP with Time Windows

**Three algorithms on a real CVRP-TW instance —  60 stops, 5 vehicles, parcel capacities, 3 delivery windows, real OSM drivable network, real OSM POI destinations — solved with classical (greedy NN), heuristic (Clarke-Wright 1964), and modern (OR-Tools GLS) approaches. Then sweep fleet size to find the diminishing-returns point.**

![3-algorithm comparison — Tbilisi CVRP-TW](assets/routes_static.png)

---

## TL;DR

A genuinely-hard last-mile dispatch problem solved three ways:

| Solver | Total time | Max single route | Per-route stops |
|---|---:|---:|---|
| **Greedy nearest-neighbour** | 346.7 min | 87.5 min | 13/12/11/12/12 |
| **Clarke-Wright savings (1964)** | **275.4 min** | 77.0 min | 16/13/11/10/10 |
| **OR-Tools (Guided Local Search)** | 276.3 min | **75.0 min** | 8/14/13/12/13 |

- **OR-Tools beats greedy by 20.3 %** on total cost.
- **Clarke-Wright (1964)** ties OR-Tools within 0.3 %. The classical heuristic still has it.
- OR-Tools wins on **max-route balance** — 75 vs 77 vs 87.5 min for the longest driver.

### Sensitivity — how cost scales with fleet size

![Sensitivity sweep](assets/sensitivity_chart.png)

- Greedy *gets worse* as you add more vehicles (more drivers each take greedy detours).
- Savings & OR-Tools plateau at ~276 min from 5 vehicles upwards.
- 4 vehicles is infeasible — demand 91 > capacity 80, plus time-window conflicts.

![Per-algorithm comparison chart](assets/comparison_chart.png)

---

## Approach

```
OSMnx drive network (3 km radius)
    ↓ truncate to largest STRONGLY-connected component
60 OSM-POI destinations + time window + parcel demand
    ↓ snap to network
NetworkX all-pairs SPL → 61×61 time matrix
    ↓
     ────────────┬─────────────────────┬───────────────────
Greedy NN              Clarke-Wright savings           OR-Tools CVRPTW + GLS
                                                          Time + Capacity dimensions
                                                          6 h slack, 10 s budget
```

Critical bug fix during development: when the cost matrix has even ONE "unreachable" entry (10M-second fallback), totals balloon to 167,000 minutes. Fixed by `ox.truncate.largest_component(G, strongly=True)`.

---

## Stack

OSMnx 2.1 · NetworkX 3.6 · OR-Tools 9.x · GeoPandas 1.1 · Folium 0.20

Single script: [`scripts/route.py`](scripts/route.py) (~400 lines).

---

## What I'd build next

1. Asymmetric (directed) time matrix — ~3–5 % improvement with one-way streets.
2. Traffic-aware edge weights from historical GPS traces.
3. Online re-optimisation when stops are delayed.
4. Multi-depot, heterogeneous fleet (already supported by OR-Tools — just config).
5. Multi-objective (total time + max route + fuel + overtime).
