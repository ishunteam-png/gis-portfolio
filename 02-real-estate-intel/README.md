# Project 2 — Real Estate Location Intelligence (Tbilisi)

**Score every 250 m cell in a city on "good place to open a new café" using FIVE open-data signals — including walkability derived from the OSM pedestrian graph — then validate the model against the existing distribution of cafés. Generalises to any OSM-mapped city via `--city`.**

![Tbilisi café suitability — hero](assets/tbilisi_georgia/suitability_hero.png)

---

## TL;DR

For Tbilisi: **8,415 cells scored over 504 km²**, top-20 ranked, and the model **passes a Spearman ρ = 0.39 validation** against the actual distribution of 869 existing cafés.

The five signals:

| Signal | Direction | Radius | Weight | Source |
|---|---|---:|---:|---|
| **Foot traffic** — shops + transit | + | 300 m | 0.30 | OSM POI |
| **Residential density** — homes within radius | + | 300 m | 0.20 | OSM building tag |
| **Tourist proximity** — attractions / hotels / museums | + | 500 m | 0.15 | OSM tourism tag |
| **Walkability** — pedestrian intersection density (deg ≥ 3) | + | 400 m | 0.20 | OSM walk graph |
| **Competition** — existing cafés | − | 200 m | 0.15 | OSM amenity=cafe |

### Top 5 candidate cells

| Rank | Lon | Lat | Score | Foot | Res | Tour | **Walk** | Comp |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 44.8020 | 41.6931 | **1.000** | 241 | 169 | 106 | **397** | 16 |
| 2 | 44.8020 | 41.6953 | 0.969 | 230 | 129 | 95 | **455** | 13 |
| 3 | 44.8050 | 41.6908 | 0.926 | 131 | 258 | 129 | **421** | 13 |
| 4 | 44.7869 | 41.7043 | 0.855 | 148 | 244 | 58 | **456** | 8 |
| 5 | 44.8050 | 41.6931 | 0.839 | 130 | 240 | 114 | **436** | 21 |

The top 4 cluster around **Mtatsminda / Old Tbilisi**. Rank 4 surfaces a Vake/Saburtalo cell with **lower foot traffic but very high walkability** — the walkability signal is doing real work.

### Validation

![Validation scatter](assets/tbilisi_georgia/validation.png)

**Spearman ρ = 0.39** (p ≈ 0). A significant positive correlation: cells the model rates highly really do already have more cafés than cells it rates lowly. The 0.4 range is right for a model that's both *aligned with reality* and *predictive beyond the obvious*.

---

## Generalises to any OSM-mapped city

```bash
py scripts/analyze.py --city "Tbilisi, Georgia"        # default
py scripts/analyze.py --city "Yerevan, Armenia"        # any place
py scripts/analyze.py --city "Sofia, Bulgaria" --validate
py scripts/analyze.py --compare                         # 3-city run
```

Auto UTM zone, auto boundary, auto OSM queries.

---

## Stack

OSMnx 2.1 · GeoPandas 1.1 · NetworkX 3.6 (walk graph) · scipy.stats (Spearman) · Folium 0.20 · matplotlib

Single script: [`scripts/analyze.py`](scripts/analyze.py) (~330 lines).

---

## Limitations and what I'd build next

1. **OSM POI coverage is uneven** — add a coverage prior down-weighting cells with low OSM edit density.
2. **No temporal foot traffic** — Mapbox Movement / SafeGraph data would replace the proxy with measured pedestrian counts.
3. **Weights are hand-picked** — with ground-truth (revenue, ratings) I'd fit weights against an outcome label.
4. **No accessibility / catchment** — walkability is currently intersection density; a 5-minute walk catchment via Dijkstra would be a 50-line addition.
5. **PostGIS layer** — for multi-city tenant version, persist all OSM pulls + scoring runs in PostGIS.
6. **Streamlit / Folium-deck** — drop GeoJSON into a Streamlit app with weights as sliders.
