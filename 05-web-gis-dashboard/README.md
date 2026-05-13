# Project 5 — Web GIS Dashboard

The whole portfolio is mostly Python scripts and static PNGs. This is the one piece a non-technical stakeholder can actually open and explore themselves. A single HTML file, no build pipeline, no framework, no backend. Just Leaflet plus a couple of CDN libraries reading the GeoJSON that Project 1 produced.

## 🚀 Live demo

**https://ishunteam-png.github.io/gis-portfolio/05-web-gis-dashboard/**

![Dashboard hero](assets/dashboard_hero.png)

## What's in it

| | |
|---|---|
| File | [`index.html`](index.html) (single file, ~500 lines of vanilla JS) |
| Data | [`data/persistent_scatterers.geojson`](data/persistent_scatterers.geojson) (45 KB, 320 PS sampled from the full pilot) |
| Dependencies | Leaflet 1.9, Chroma.js 2.4, both from CDN |
| Build step | none |

What the dashboard does:

1. **Six one-click presets.** "All PS", "Subsidence ≥ 3 mm/yr", "Severe (≥ 5)", "Stable band (±1)", "Strong east motion", "Reset". Each clicks the right filter values and colour mode into place.
2. **Split view.** Toggle a side-by-side mode where the left map shows vertical velocity and the right shows east-west. Pan/zoom on either, the other follows. Useful for the question "do the subsiding cells also have a horizontal component?"
3. **Live histogram.** A small Canvas histogram in the sidebar shows the V_U distribution of *currently-visible* points (after filters apply). Bars are coloured with the same diverging ramp as the map.
4. **URL hash state.** Every filter, colour mode, and toggle gets encoded in the URL hash. There's a "Copy shareable URL" button. Paste it into another browser and you see exactly the same view I was looking at. This is what makes the dashboard *collaborative* rather than just *interactive*.
5. **Per-PS popups** with vertical, east-west, both coherences, lat/lon.
6. **Top-20 highlight toggle** — yellow rings around the 20 most-subsiding PS in the current filter window.
7. **Live stat cards** in the header showing the count and the mean/min/max V_U of the visible set.

## Why a single file, no framework

Three reasons:

- **Portability.** It runs on GitHub Pages, S3, a USB stick, anywhere. No build, no Webpack, no Node version pinning.
- **Auditability.** A reviewer can read every line of dashboard logic in one screen scroll. There are no framework abstractions hiding what's happening.
- **Performance.** With `preferCanvas: true`, Leaflet draws all 320 points as Canvas circles in one pass. Filter changes re-render in <50 ms. A React equivalent would be 5–10x slower at this point count for no UX benefit.

When the data grows past ~100,000 points the single-file approach hits its limit and you need vector tiles (PMTiles via maplibre-gl is the modern stack). Below that, this is the right architecture.

## Screenshots

![All PS coloured by V_U with histogram + presets + AOI outline](assets/dashboard_hero.png)

![Top-20 most-subsiding highlighted with yellow rings](assets/dashboard_top20.png)

![V_E mode with V_U max filter applied, showing only actively-subsiding PS](assets/dashboard_ve_filter.png)

## Run it locally

```bash
cd 05-web-gis-dashboard
py -m http.server 8000
# then open http://localhost:8000/index.html
```

Deploy: drop the folder onto any static host. No build command.

## What I'd add next

A small time-series sparkline in each PS popup, since the underlying data has 3 years of LOS samples that the dashboard isn't currently surfacing. Then drag-rectangle selection to export a subset as GeoJSON. Then a "catalogue mode" that turns the same code into a generic GeoJSON viewer for any numeric property — which would also work for Projects 2, 4, and 6.
