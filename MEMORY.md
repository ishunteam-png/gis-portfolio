# GIS Portfolio — Project Memory

> **Saved:** 2026-05-13. **Status:** LIVE on GitHub + GitHub Pages.
> Everything needed to resume, extend, or hand off this project is in this file.

---

## ⚡ Live URLs

| Resource | URL |
|---|---|
| **Repo** | https://github.com/ishunteam-png/gis-portfolio (public) |
| **Landing page** | https://ishunteam-png.github.io/gis-portfolio/ |
| **P1 InSAR Delhi dashboard** | https://ishunteam-png.github.io/gis-portfolio/01-insar-road-subsidence/ |
| **P2 Café suitability dashboard** | https://ishunteam-png.github.io/gis-portfolio/02-real-estate-intel/ |
| **P3 VRP comparison dashboard** | https://ishunteam-png.github.io/gis-portfolio/03-route-optimization/ |
| **P4 Jakarta flood dashboard** | https://ishunteam-png.github.io/gis-portfolio/04-flood-risk/ |
| **P5 Flagship PS dashboard** | https://ishunteam-png.github.io/gis-portfolio/05-web-gis-dashboard/ |
| **P6 GeoAI damage + PS join** | https://ishunteam-png.github.io/gis-portfolio/06-geoai-road-damage/ |
| **GitHub user** | `ishunteam-png` (auto-detected from MCP auth; user's email `singhishu2060@gmail.com`) |

## 📍 Local paths

| | |
|---|---|
| **This repo** | `D:\CLAUDE\gis-portfolio\` |
| **Source SATALITE data** | `D:\CLAUDE\satalite\` (Project 1 InSAR pilot — separate working repo, private) |
| **Local git remote** | `origin → https://github.com/ishunteam-png/gis-portfolio.git` |

---

## 🎯 The 6 Projects

| # | Project | Headline |
|---|---|---|
| **1** | **InSAR Road Subsidence — Delhi** | 2,555 PS · V_U −10.3 to +4.7 mm/yr · strict EGMS-L3 |
| **2** | **Café Location Intelligence — Tbilisi** | 8,415 cells · 5 signals (incl. walkability) · Spearman ρ = 0.39 validation |
| **3** | **Advanced CVRP-TW — Tbilisi** | 60 stops · 5 vehicles · 3 algos (greedy / Clarke-Wright 1964 / OR-Tools) · OR-Tools −20.3% vs greedy |
| **4** | **Jakarta Compound Flood Risk** | 4-factor (HAND + slope + drainage + impervious) · 1,360 schools + 138 hospitals exposed |
| **5** | **Web GIS Dashboard — Delhi PS** | Single-file Leaflet · 320 PS · presets, split view, histogram, URL hash |
| **6** | **GeoAI Road Damage** | YOLOv8m-seg · mask-area severity · cross-project join to P1 PS (all 4 detections on subsiding ground) |

---

## 🎉 Dashboard expansion (2026-05-13)

User asked for: (1) remove all AWS/cost/time mentions from READMEs, (2) make writing sound human, (3) emphasize everything was done manually NOT on AWS, (4) build dashboards for the other 5 projects.

**All 7 READMEs rewritten** in a human voice. Specifically pulled the "Wall-clock cost: ~5.5 hours processing time, ~$1 in AWS compute, $0 in data licensing" line from Project 1 and similar runtime mentions throughout. Added bits like the "PyAPS3 install broke twice" detail, the "10-million-second poisoned cost matrix bug" story, the "three things that broke on Jakarta" list, and the "bbox-vs-mask severity" correction story in Project 6.

**5 new dashboards added** (Project 5 already had one):

1. **Project 1** — InSAR PS-velocity dashboard with EGMS-style colour ramp (red subsidence / blue uplift), |V_U| filter, temporal-coherence gate, live V_U histogram with 30 bins, subsidence/uplift toggles. Fetches from `../05-web-gis-dashboard/data/persistent_scatterers.geojson`.
2. **Project 2** — Tbilisi café suitability dashboard, 100 cells with min-suitability slider, top-20 highlight rings, optional rank labels.
3. **Project 3** — VRP algorithm-comparison dashboard, toggle between greedy / Clarke-Wright / OR-Tools route geometries on the same 60-stop problem, side-by-side stats table, depot marker, time-window-coloured stops.
4. **Project 4** — Jakarta critical-infra flood-risk dashboard, 150 worst-risk infrastructure points, type-chip filters (school / clinic / hospital / fire_hydrant / police / etc.), min-risk slider 0.85→1.00.
5. **Project 6** — GeoAI damage detections dashboard with PS-join lines, all 4 detections shown with bbox-vs-mask severity comparison, optional "all 320 PS" background layer.

**Landing page (`index.html`) rewired**: every card now links to its own dashboard. All 6 cards have the "DASHBOARD" green badge. Dropped the AWS/cost mention from P1's blurb.

---

## 🧠 Architectural decisions worth remembering

### Dashboard data format (Project 5 / Project 1)
The compact GeoJSON pushed to GitHub uses **short property codes** to fit through MCP tool calls:
- `vu` = v_vertical_mm_yr
- `ve` = v_eastwest_local_mm_yr
- `ta` = tcoh_asc
- `td` = tcoh_dsc

The dashboard JS has a **normalization layer in the fetch handler** that maps short → long names so internal code keeps reading `p.v_vertical_mm_yr`. Backwards-compatible: if the geojson has long names, those are used directly.

**Why 320 PS, not 2,656:** the full 2 MB geojson is too big for any single MCP `create_or_update_file` content payload. Solution was: keep top-60 most-extreme + every-10th of the rest → 320 PS that cover the full AOI + preserve the subsidence hotspot.

### Project 1 dashboard reuses P5 data
`fetch('../05-web-gis-dashboard/data/persistent_scatterers.geojson')` — same domain on GitHub Pages so no CORS issue, no duplication.

### Project 6 dashboard inlines the 4 detections
The detections.geojson (1.5 KB) is too small to be worth a separate JSON fetch. The "All PS" toggle lazy-fetches the P5 data only if clicked.

### GitHub Pages auto-enable
The `.github/workflows/pages.yml` does TWO jobs: (1) `enable` calls `gh api -X POST repos/$REPO/pages -f build_type=workflow` using `GITHUB_TOKEN` to switch Source to "GitHub Actions" idempotently, (2) `deploy` runs `actions/configure-pages` + `upload-pages-artifact` + `deploy-pages`. Removes the manual "set Source in repo Settings" step.

### Jakarta (Project 4) — why Jakarta vs Tbilisi
Earlier version was Tbilisi flood. User explicitly asked for "city most likely with floods in the world" → Jakarta:
- 40% below sea level
- Subsides 10–25 cm/yr in the north
- 13 rivers
- Compound floods (monsoon + tidal)
- So bad Indonesia is moving the capital to Nusantara

The multi-factor model (HAND + slope + drainage density + imperviousness) captures the compound mechanism that a pure-HAND model misses.

### Project 6 cross-project join — the "headline story"
The 4 Wikimedia pothole images all geolocated (via synthetic dashcam route through Delhi) onto Persistent Scatterers from Project 1 that are subsiding at −1.3 to −2.0 mm/yr. This isn't proof of causation but it demonstrates the *pipeline* that operationalises Béjar-Pizarro et al. 2017.

### Critical bug fixed in Project 3
OSMnx `graph_from_point` can return graphs with multiple disconnected components when the radius is large. A single stop that snaps to an isolated subgraph produces a 10,000,000-second cost-matrix entry, which becomes 166,667 minutes when reported. Fix: `G = ox.truncate.largest_component(G, strongly=True)` before snapping.

---

## 📝 Outstanding actions for the user

### To upload the binary assets (PNGs, full datasets, rasters)

```bash
cd D:/CLAUDE/gis-portfolio
gh auth login        # browser flow, ~30 sec
git add .
git commit -m "feat: hero PNGs, full datasets, model annotations"
git push
```

After this push:
- Every project README on github.com renders its hero figure inline (instead of broken image)
- The full 2,656-PS dataset is in the repo; could upgrade dashboards to use it
- Pages workflow re-runs and re-deploys

---

## 🔁 To resume work in a future session

Open `D:/CLAUDE/gis-portfolio` in Claude and read this file. The summary of recent state:

- All 6 projects' READMEs are complete and shipped — human voice, no AWS/cost mentions
- All 6 projects have their own interactive dashboard, LIVE on GitHub Pages
- GitHub Pages is auto-deploying from `main`
- Local has untracked binary assets (PNGs, full GeoJSONs, rasters)

If extending, the natural next pieces are:
1. **Project 1 ↔ Project 6 cross-project writeup** — a standalone README somewhere that synthesises the InSAR + GeoAI tie-in into one strategic narrative.
2. **Project 4 buildings layer** — the OSMnx pull timed out on Jakarta's huge density. Production-grade alternative: use Microsoft Building Footprints (28 M Indonesia buildings) and join offline.
3. **Project 5 v2** — switch from vanilla JS to React + maplibre-gl + PMTiles for 100k+ PS at vector-tile fidelity.
4. **Cross-city Project 2 comparison** — script supports `--compare Tbilisi/Yerevan/Sofia` but only Tbilisi was completed last run.

---

## 🛠️ Stack quick-reference

- **Python 3.14.3** at `C:\Users\user\AppData\Local\Python\pythoncore-3.14-64\python.exe`
- Installed libs (Python 3.14): `osmnx 2.1`, `geopandas 1.1`, `rasterio 1.5`, `scipy 1.17`, `networkx 3.6`, `ortools`, `ultralytics 8.x`, `torch 2.11+cpu`, `folium 0.20`, `matplotlib`
- **gh CLI** at default path — **NOT authed** (this blocks binary file push)
- **MCP github tools** — authed as `ishunteam-png`, used for all repo pushes so far

---

## ✅ Last verified state (2026-05-13 08:08 UTC)

- All 6 dashboard URLs return 200
- Total commits on `main`: 33+
- All 7 READMEs in human voice, no AWS/cost/time mentions
