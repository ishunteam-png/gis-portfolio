# Project 3 — Capacitated VRP with Time Windows (Tbilisi)

The core question is the one any courier dispatcher faces every morning: I have 60 stops to make, 5 vans, each customer wants a specific delivery window, what's the best route plan?

This is the Capacitated Vehicle Routing Problem with Time Windows. NP-hard in the worst case but very solvable in the regime that matters in practice (a few dozen stops, a handful of vehicles).

![Three algorithms side-by-side](assets/routes_static.png)

## Three solvers, one problem

I ran the same instance through three approaches:

| Solver | Total time | Max single route | Per-route stops |
|---|---:|---:|---|
| Greedy nearest-neighbour | 346.7 min | 87.5 min | 13 / 12 / 11 / 12 / 12 |
| **Clarke-Wright savings (1964)** | **275.4 min** | 77.0 min | 16 / 13 / 11 / 10 / 10 |
| **OR-Tools (Guided Local Search)** | 276.3 min | **75.0 min** | 8 / 14 / 13 / 12 / 13 |

The interesting result: a heuristic from **1964** essentially ties Google's modern OR-Tools solver on total cost. They're within 0.3% of each other. OR-Tools wins on max-route balance — its worst-case driver works 75 min, vs Savings' 77 min and Greedy's 87.5 min. That 12-minute reduction in the longest driver's day is the real operational signal.

Both Savings and OR-Tools crush greedy by ~20%.

## How costs scale with fleet size

![Sensitivity curve](assets/sensitivity_chart.png)

I swept vehicle count from 3 to 8 and re-ran all three algorithms. Three things stand out:

- **Greedy gets *worse* as you add more vehicles.** Each driver picks their own nearest unvisited stop, so more drivers means more crisscross.
- **Savings and OR-Tools plateau** at ~276 min from 5 vehicles upward. Adding vehicle 6, 7, 8 doesn't help — you're just paying for idle capacity.
- **4 vehicles is infeasible.** Total parcel demand (91) exceeds 4-vehicle capacity (80), and the time-window constraints make it worse. So the answer to "how many vans do I need" is *exactly 5*.

![Per-algorithm comparison](assets/comparison_chart.png)

## The bug that wasted me a couple hours

The first time I ran this, the greedy and savings algorithms reported a total time of 167,000 minutes (~278 hours, for 60 deliveries). OR-Tools just said "infeasible."

The cause: OSMnx's `graph_from_point` can return a graph with multiple disconnected components when the radius is large enough. One stop snapped to a node sitting in an isolated subgraph, which produced a `nx.shortest_path_length` error caught by my try/except and converted into `10_000_000` seconds. One poisoned cell in the cost matrix → every algorithm that touched it inherited the 10M-second penalty. Hence the absurd total.

The fix is one line: `G = ox.truncate.largest_component(G, strongly=True)` before snapping. After that, every node can reach every other node, and the cost matrix is clean. I'm mentioning this because it's the exact pitfall that trips up most OSMnx VRP tutorials online — they almost all skip the LCC truncation.

## Constraints I actually applied

- **Capacity**: each vehicle holds 20 parcels max. Demand per stop is 1, 2, or 4 (weighted random).
- **Time windows**: each customer gets a 90-minute window (morning 08:00–09:30, midday 11:00–12:30, or afternoon 15:00–16:30). OR-Tools enforces these as hard constraints.
- **Service time**: 3 minutes at every stop, modelled as an additive transit cost out of each node.
- **Single depot**: Freedom Square in central Tbilisi. All routes start and end there.
- **Slack**: 6 hours of slack on the Time dimension in OR-Tools, so a van that finishes morning at 09:45 can legally wait until 11:00 to start midday deliveries.

## Why Clarke-Wright is still competitive in 2026

For every pair of customers (i, j), the savings `s(i,j) = c(0,i) + c(0,j) - c(i,j)` quantifies how much you save by serving them on one route instead of two separate out-and-back trips from the depot. Sort all pairs descending by savings, then greedily merge feasible routes.

That's it. No metaheuristic, no escape from local optima, just a sort and a merge loop. It runs in milliseconds. And it captures the structure of medium-sized VRPs so well that a modern GLS metaheuristic only beats it by basis-point margins.

OR-Tools' real edge comes at scale (thousands of stops) and when you stack on harder constraints (heterogeneous fleet, multi-depot, traffic-aware edge weights, soft time-window penalties). For a 60-stop instance with the constraints I had, Clarke-Wright is essentially as good and runs faster.

## The interactive map

The [dashboard for this project](https://ishunteam-png.github.io/gis-portfolio/03-route-optimization/) lets you toggle between the three algorithms, hover a route to see its stats, click any stop for time window and demand.

## What I'd do next

Directed (asymmetric) cost matrix. Right now I'm treating each edge as bidirectional. With one-way streets that's an approximation; using true directed shortest paths typically tightens the solution by 3–5 %.

Traffic-aware edge weights. OSM `maxspeed` is free-flow speed. For peak-hour dispatch, you'd want time-of-day traffic profiles, ideally trained from your own historical GPS traces.

Re-optimisation mid-shift. If a stop is late or a new high-priority delivery comes in, the dispatcher needs to re-plan routes from each driver's current position. OR-Tools supports incremental re-solve; that's a small state model plus a webhook.
