# Project 5 — Web GIS Dashboard (advanced)

**Single-file Leaflet dashboard for the Project 1 Delhi PS dataset, with one-click presets, side-by-side split view, live histogram, shareable URL state, and zero build pipeline. ~480 lines of vanilla JS.**

## 🚀 Live demo

**https://ishunteam-png.github.io/gis-portfolio/05-web-gis-dashboard/**

![Dashboard hero](assets/dashboard_hero.png)

---

## TL;DR

A working geospatial dashboard for the Delhi InSAR Persistent Scatterers, built as **one HTML file** with no build pipeline. Just Leaflet + Chroma.js from CDN reading the project's GeoJSON.

| | |
|---|---|
| **File** | [`index.html`](index.html) (single file, ~480 lines) |
| **Data** | [`data/persistent_scatterers.geojson`](data/persistent_scatterers.geojson) (stratified-sample for live demo; full 2,656 PS for local) |
| **Dependencies** | Leaflet 1.9, Chroma.js 2.4 (both CDN) |
| **Build step** | none — open over HTTP, works |

---

## Features (v2)

1. **One-click presets** — six curated filter combinations.
2. **Split view** — toggle side-by-side V_U / V_E maps that pan/zoom together.
3. **Live histogram** — Canvas histogram of currently-visible V_U distribution.
4. **URL hash state + Copy link** — every filter encoded in the URL; "Copy shareable URL" puts it on your clipboard.
5. **Six colour modes** — V_U, V_E, LOS ASC, LOS DSC.
6. **Live stat cards** — visible count, mean/min/max V_U recompute on every drag.
7. **Per-PS popups** with all attributes.
8. **AOI outline toggle**.
9. **Canvas-mode rendering** for sub-50 ms filter response.

---

## Screenshots

### Default — all PS coloured by V_U, with histogram, stats, presets, AOI outline
![Dashboard hero](assets/dashboard_hero.png)

### Top-20 most-subsiding highlighted
![Top-20 highlight](assets/dashboard_top20.png)

### V_E mode with V_U filter
![V_E filter](assets/dashboard_ve_filter.png)

---

## Run it locally

```bash
cd 05-web-gis-dashboard
py -m http.server 8000
# → http://localhost:8000/index.html
```

Deploy: GitHub Pages / Cloudflare Pages / Vercel — no build command.

---

## What I'd build next

1. Time-series sparkline in popup.
2. Box-select export (drag rectangle, download subset).
3. Catalogue mode — drop in any GeoJSON, auto-build colour scale + histogram.
4. Vector-tile mode (PMTiles + maplibre-gl) for 100k+ PS.
5. React v3 when single-file architecture is outgrown.
