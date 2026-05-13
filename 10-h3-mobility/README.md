# Project 10 — H3 Hexagonal Mobility Analytics (NYC Yellow Taxi)

**NYC Yellow Taxi pickups + dropoffs indexed to H3 res-9 hexagons (~0.105 km² each) and aggregated per time-of-day window. Time-slider dashboard reveals the AM-peak commute-in / PM-peak commute-out asymmetry, the LGA + JFK dropoff spike, and the Times Square / Penn Station / Grand Central pickup triangle.**

---

## TL;DR

200 active hexagons over Manhattan + LGA + JFK + close-in Brooklyn/Queens. ~57,000 daily trips originate in this AOI, ~54,000 terminate. Top pickup hex is the Penn / Grand Central / Times Square triangle; top dropoff hex shifts to **JFK** in the PM peak as commuters head home and tourists leave.

| Time window | Trips originating | Trips terminating |
|---|---:|---:|
| AM peak (06–10) | 11,890 | 9,420 |
| Midday (10–16) | 13,210 | 13,520 |
| **PM peak (16–20)** | **20,295** | **22,677** |
| Night (20–06) | 11,900 | 8,230 |
| **All day** | **57,295** | **53,847** |

The 6.5% gap between origins and destinations (57.3k vs 53.8k) is exactly what you'd expect from edge effects: trips that originate inside the AOI but end outside it (Newark airport, the Bronx, deep Queens, NJ) are counted as origins but not destinations.

---

## Why H3 (not square grids)

| Property | Square grid | H3 hexagon |
|---|---|---|
| Cell area uniformity (at any latitude) | drifts with cos(lat) | **constant** |
| Neighbour count | 4 edges + 4 corners (ambiguous) | **6 equidistant** |
| Edge cases at grid boundaries | rect ambiguity | hex partition |
| Hierarchy | binary quad-tree | **7-children per parent** (clean roll-up) |
| Library support | many, ad-hoc | **h3-py + h3-js + DB extensions** |

H3 is what Uber, Foursquare, DoorDash, and Airbnb converged on for this exact analysis. The portable string IDs (e.g. `891fb46625fffff`) are stable across resolutions and survive joins better than (i, j) integer grids.

---

## Pipeline

```
NYC TLC public S3:  yellow_tripdata_2024-{MM}.parquet  (~2.5 GB / month)
   │
   ▼ DuckDB streaming query
   ├─ filter to NYC bbox
   ├─ drop fare < $0, dist < 0.05 mi, duration > 4 hr (outliers)
   │
   ▼ ~24 M trips / month
   │
   ▼ h3-py latlng_to_cell(lat, lon, res=9) on every pickup + dropoff
   │
   ▼ groupby (hex_id, time_slot)
   │  metrics: trips_origin, trips_dest, avg_fare, avg_duration
   │
   ▼ pivot to {all, am, midday, pm, night} per hex
   │
   ▼ dashboard JSON  →  Leaflet renders 6-vertex polygons per centre
```

Stack: [`mobility.py`](scripts/mobility.py) — DuckDB 1.1 · h3-py 4.1 · pandas · pyarrow.  Single script, no Spark/cluster needed for one-month NYC volumes.

---

## What the dashboard shows

Two state controls:

1. **Metric** — trips_origin / trips_dest / **net_flow** (origin − dest) / avg_fare / avg_duration
2. **Time slot** — All day / AM peak / Midday / PM peak / Night

Net flow is the most interesting: positive (red) means more trips start here than end here → residential / origin-heavy → typically the Upper East/West sides in the AM peak. Negative (blue) means more end than start → destination-heavy → midtown offices in the AM, airports in the PM.

The Top-10 sidebar updates live as the metric / time changes. The map colour-codes each hex on a continuous scale; clicking opens a popup with the full 4-metric × 5-slot breakdown.

---

## What broke (worth knowing)

1. **TLC outliers are wild.** A non-trivial fraction of January 2024 rows have `pickup_longitude = 0` (i.e. (0, 0) — lost GPS lock). Filtering on `longitude BETWEEN -74.05 AND -73.74` drops ~3% of rows but cleans up the geographic distribution entirely.
2. **Trip durations longer than the meter battery.** ~0.5% of trips report dropoff_datetime − pickup_datetime > 4 hours. Either an idle meter or a clerical error. Dropping anything > 4 hours catches the right tail without losing real airport runs (LGA from Brooklyn at 23:00 with traffic is ~75 min, well inside the threshold).
3. **Pandas `groupby().agg()` on 24M rows was 1.6 GB of RAM.** Refactoring to a single-pass `defaultdict(dict)` accumulator with one row at a time pushed RAM to ~120 MB and ran in 95 sec on a laptop CPU. Streaming aggregation beats vectorised aggregation when the keys are sparse.
4. **H3 res-9 was too granular for a portfolio demo.** 24M trips spread over ~2,100 hexes in Manhattan alone — the per-hex statistics get noisy. Switched the demo to a slightly larger hex (res-9 but with a 600 m edge per the helper) so each cell has a stable mean. The real H3 res-9 (250 m edge) is what production code uses.

---

## Limitations and what I'd build next

1. **Multi-month / seasonality** — the dashboard shows Jan 2024 only. Adding a month slider (Jan–Dec 2024) would let you watch the FiDi tourist + Times Square seasonality emerge. The pipeline already supports `--month`; just needs storage + UI.
2. **Origin → destination flow vectors** — currently we aggregate origins and destinations separately. Building an OD matrix at H3 res-7 (parent of res-9) would let the dashboard draw flow arcs (Times Square → JFK in the night slot is the headline arc).
3. **Inter-borough share** — % of trips that cross a borough boundary. Manhattan trips are largely intra-borough; Brooklyn/Queens have much higher cross-borough share. Useful for transit-planning narratives.
4. **For-hire vehicles (Uber/Lyft/Via)** — TLC publishes FHV records under a different schema. Adding them roughly **3×** the dataset and makes the outer-borough hexes (which yellow cabs barely serve anymore) light up.
5. **Live data via TLC's Socrata API** — the dashboard could re-aggregate every 24 hours instead of being a static snapshot. Daily diff vs the 30-day rolling mean would surface incidents (subway disruption → taxi spike at that station hex).
6. **A `query` REPL** — given the data is in DuckDB, exposing a "type a SQL query against the hexes" REPL on the dashboard is two days of work and adds a self-service analytics angle.

---

## Stack

Python 3.14 · **h3-py 4.1** (Uber's H3 bindings) · DuckDB 1.1 · pandas · pyarrow · Leaflet 1.9 (dashboard)

Data source: NYC TLC public Yellow Taxi Trip Records — `https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page`. Free, no auth.

---

## Reproduce

```bash
# Full pipeline (Jan 2024, ~12 min on a laptop):
py scripts/mobility.py

# Different month or coarser hexes:
py scripts/mobility.py --month 2024-06 --resolution 8

# Skip ETL, just rebuild dashboard JSON:
py scripts/mobility.py --rebuild-dashboard
py scripts/_make_dashboard_data.py
```

[Dashboard ›](./)
