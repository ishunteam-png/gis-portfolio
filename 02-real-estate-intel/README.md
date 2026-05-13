# Project 2 — Café Location Intelligence (Tbilisi)

If you were going to open a new café in Tbilisi, where would you put it?

This project tries to give an actual answer: every 250 m cell in the city scored on five open-data signals, then validated against where cafés already exist.

![Tbilisi suitability map with top-20 cells outlined](assets/tbilisi_georgia/suitability_hero.png)

## The five signals

All from OpenStreetMap and the OSM walk graph. Each is computed in a small radius around the cell centre and normalised.

| Signal | Direction | Radius | Weight |
|---|---|---:|---:|
| Foot traffic (shops + transit stops nearby) | + | 300 m | 0.30 |
| Residential density (homes nearby) | + | 300 m | 0.20 |
| Tourist amenities (attractions, hotels, museums) | + | 500 m | 0.15 |
| Walkability (street-intersection density, deg ≥ 3) | + | 400 m | 0.20 |
| Competition (existing cafés nearby) | − | 200 m | 0.15 |

Min-max normalise each, weighted sum, normalise the result. Top-20 highest-scoring cells get surfaced.

## The top five cells

| Rank | Lon | Lat | Score | Foot | Res | Tour | Walk | Competition |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 44.802 | 41.693 | **1.000** | 241 | 169 | 106 | **397** | 16 |
| 2 | 44.802 | 41.695 | 0.969 | 230 | 129 | 95 | **455** | 13 |
| 3 | 44.805 | 41.691 | 0.926 | 131 | 258 | 129 | **421** | 13 |
| 4 | 44.787 | 41.704 | 0.855 | 148 | 244 | 58 | **456** | 8 |
| 5 | 44.805 | 41.693 | 0.839 | 130 | 240 | 114 | **436** | 21 |

The top 4 all cluster around **Mtatsminda / Old Tbilisi** — which matches reality, that's where the successful cafés actually are. Rank 4 is the one I find most interesting: it surfaces a Vake/Saburtalo cell with merely OK foot traffic but extremely high walkability. Pure POI-density wouldn't have picked it; the walkability signal is doing real work.

## Does the model agree with reality

![Validation scatter](assets/tbilisi_georgia/validation.png)

For every cell, plot the model's suitability score against the number of cafés actually observed in that cell. Spearman ρ = **0.39** (p ≈ 0). That's a significant positive correlation: cells the model rates highly really do already have more cafés than cells it rates lowly.

The correlation isn't 1.0, and that's the point. If it were 1.0 the model would just be re-discovering competition density and wouldn't tell you anything new. ~0.4 is the right zone for a model that's both calibrated to reality *and* able to recommend underserved spots.

## Diagnostics — all five components

![Score components](assets/tbilisi_georgia/score_components.png)

Every signal across the city before normalisation. This is the "show your working" panel. The signals are visibly independent of each other: foot traffic peaks in different cells than walkability, which peaks in different cells than residential density. So the composite isn't just a recolouring of one dominant signal.

## Walkability standalone

![Walkability panel](assets/tbilisi_georgia/walkability_panel.png)

Intersection density (graph nodes with degree ≥ 3) within 400 m, computed from the OSM walk graph. The bright orange ridge runs through Mtatsminda → Vake → Saburtalo, which is also where the top-5 cells cluster. The walk graph has 62,849 such nodes for Tbilisi.

## Run it on any city

The script accepts `--city`:

```bash
py scripts/analyze.py --city "Tbilisi, Georgia"
py scripts/analyze.py --city "Yerevan, Armenia"
py scripts/analyze.py --city "Sofia, Bulgaria" --validate
py scripts/analyze.py --compare
```

UTM zone, boundary, and all OSM queries auto-adapt to wherever you point it.

## The interactive map

The [dashboard for this project](https://ishunteam-png.github.io/gis-portfolio/02-real-estate-intel/) lets you pan the city, hover any cell for its score breakdown, and filter the visible cells by a minimum threshold.

## What I'd do next

The weights are hand-picked, which is defensible but not satisfying. If I had ground-truth (revenue numbers, Yelp ratings, closure rates) I'd fit weights against an outcome label rather than guessing them.

Also, the OSM foot-traffic proxy is exactly that — a proxy. Real foot-traffic data from Mapbox Movement, SafeGraph, or anonymised mobile-location data would replace it with measured counts, which would change which cells rank highest in non-trivial ways.

The walkability term right now is just intersection density. A real accessibility score would compute the 5-minute-walk catchment via Dijkstra on the pedestrian graph and use the catchment population/POI counts.
