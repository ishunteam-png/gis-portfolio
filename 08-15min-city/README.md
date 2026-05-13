# Project 8 — 15-Minute City Accessibility (Paris)

**Operationalises Carlos Moreno's *Ville du quart d'heure* thesis. Every grid cell in Paris intra-muros is scored on whether residents can walk to each of six essential categories — live, work, supply, care, learn, enjoy — within 15 minutes along the real OSM pedestrian network. Plus 5/10/15-min isochrones for 8 anchor Métro stations.**

---

## TL;DR

Paris is the textbook 15-min city — and the numbers back it up.

| Score (categories reachable in 15 min) | % of grid cells |
|---:|---:|
| **6 / 6** | **58.6%** |
| 5 / 6 | 29.1% |
| 4 / 6 | 3.2% |
| 3 / 6 | 1.6% |
| 2 / 6 | 7.0% |
| 1 / 6 | 0.5% |
| 0 / 6 | 0.0% |

**87.7%** of cells reach at least 5 of 6 essential categories within a 15-min walk. The 7% scoring 2/6 are almost all inside **Bois de Boulogne** and **Bois de Vincennes** — the two big peripheral parks, where you walk 10+ min just to leave the woods.

---

## The six categories (after Moreno 2016)

| Category | OSM tags used |
|---|---|
| 🏠 **Live** | `building=residential` density |
| 💼 **Work** | `office=*`, `amenity=coworking_space` |
| 🛒 **Supply** | `shop=supermarket / convenience / greengrocer / marketplace` |
| 🏥 **Care** | `amenity=pharmacy / clinic / hospital / dentist / doctors` |
| 🎓 **Learn** | `amenity=school / university / college / library` |
| 🎭 **Enjoy** | `leisure=park / garden`, `amenity=restaurant / cafe / bar / cinema / theatre` |

A cell "reaches" a category if **at least one POI** in that category sits within 1,250 m **along the real OSM walk graph** — not 1,250 m as the crow flies. That's the Carlos Moreno spec; Euclidean approximations over-count by 15–30%.

---

## Pipeline

```
OSMnx → Paris pedestrian graph (47,812 nodes / 71,438 edges)
   │     [largest weakly-connected component only — same bug as Project 3]
   │
   ▼
For each of the 625 grid cells (350 m each):
   ├─ snap centroid to nearest walk-graph node
   ├─ single-source Dijkstra capped at 1,250 m
   └─ for each of 6 categories, check if any POI is in the reached set
   │
   ▼
Score = count of reachable categories (0..6)
   │
   ▼
For 8 showcase Métro stations:
   ├─ single-source Dijkstra at 420 m, 830 m, 1,250 m (5/10/15 min)
   ├─ collect reached nodes
   └─ alpha-shape concave hull → isochrone polygon
```

Single script: [`scripts/accessibility.py`](scripts/accessibility.py). Generalises to any city via `--city`. Stack: OSMnx 2.1 · NetworkX 3.6 · Shapely 2.0 · alphashape 1.3 · GeoPandas 1.1.

---

## Showcase stations

Eight anchor Métro stations, each with full 5/10/15-min isochrones + POI counts in the 15-min walk:

| Station | Live | Work | Supply | Care | Learn | Enjoy |
|---|---:|---:|---:|---:|---:|---:|
| **Châtelet** | 1620 | **1810** | 71 | 88 | 45 | **487** |
| **République** | 1860 | 920 | 64 | 95 | 38 | 312 |
| **Bastille** | 1740 | 530 | 58 | 73 | 34 | 298 |
| **Belleville** | 2110 | 280 | 52 | 64 | 27 | 196 |
| **Montparnasse** | 1980 | 640 | 60 | 71 | 36 | 244 |
| **Trocadéro** | 1230 | 450 | 39 | 52 | 24 | 187 |
| **Stalingrad** | 1850 | 320 | 47 | 56 | 22 | 174 |
| **Nation** | 1980 | 410 | 53 | 67 | 31 | 218 |

Châtelet is the unsurprising peak — central Paris, Les Halles, the densest employment + culture mix in Île-de-France. Belleville is the *residential* peak: 2,110 housing POIs in the 15-min walk, which is in line with its identity as a young, dense, immigrant-heavy quartier in the 19e/20e.

---

## What broke (worth knowing)

1. **OSMnx walk graph wasn't strongly connected.** Three small islands near Île aux Cygnes were isolated subgraphs. Same bug as Project 3 — a few cells snapped to those nodes and produced 0-reachable-categories scores. Fixed with `ox.truncate.largest_component(G, strongly=False)` (weakly is enough for walk graphs; strong-connectivity matters more for driving where one-ways exist).
2. **POIs at building polygons need `.representative_point()`, not `.centroid`.** Le Bon Marché has a centroid that lands inside the building footprint, but the building footprint touches a private courtyard not reachable from the public street network. `representative_point()` always falls *inside* the polygon AND I added a fallback that snaps to the building's nearest publicly-walkable street node.
3. **Alphashape `alpha=0.005` for 5-min, `0.003` for 15-min.** Too tight and the polygon has holes inside the isochrone. Too loose and 5-min isochrones look like 10-min ones. Tuned per-radius.
4. **The Métro doesn't count.** Carlos Moreno's spec is *walking* only — adding the Métro into the graph would let you "reach" the Eiffel Tower from Bastille in 15 min, which defeats the point. Walk graph only.

---

## Limitations and what I'd build next

1. **Population weighting** — currently every cell has equal weight. Adding INSEE Iris-level population would let me say "X% of *people* live in a full 15-min city", not "X% of *cells*". That's the stat policymakers actually want.
2. **Time-of-day variation** — schools and shops have hours. A pharmacy at 03:00 isn't reachable in the way it is at 14:00. The OpenStreetMap `opening_hours` tag plus a per-cell hourly score would expose the night-time accessibility gap.
3. **Quality, not just presence** — a 24/7 corner-store is not equal to a Carrefour. Adding POI quality / size proxies (OSM `building:flats`, Google Places rating) would distinguish "supply" from "real supply".
4. **Multi-mode** — the dashboard could let you toggle walk-only vs walk+bike. For Paris-with-Vélib' that adds a huge layer of accessibility, especially outside the 1er–8e.
5. **Cross-city baseline** — Paris's 88% is good. What's London's? Lagos's? The script generalises via `--city`; running it on 20 cities would give a real ranking.
6. **Population-served-by-isochrone** — the 8 showcase stations are interesting *individually*. The right policy metric is the *union* of all 304 Métro stations' 15-min isochrones, intersected with population. That's the city's serviceable population by walking from transit alone.

---

## Stack

Python 3.14 · OSMnx 2.1 · NetworkX 3.6 · Shapely 2.0 · alphashape 1.3 · GeoPandas 1.1 · Leaflet 1.9 (dashboard)

Data sources: OpenStreetMap (walk graph + POIs) — pulled live with no API key.

---

## Reproduce

```bash
py scripts/accessibility.py                       # Paris (default)
py scripts/accessibility.py --city "Lyon, France"
py scripts/accessibility.py --walk-min 10         # 10-min city variant
py scripts/_make_dashboard_data.py                # regenerate JSON only
```

[Dashboard ›](./)
