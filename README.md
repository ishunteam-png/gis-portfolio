# GIS / Geospatial Portfolio — ISHU

Ten projects I built over the past few months while getting more serious about GIS. Each one tries to answer a real spatial question, runs end-to-end from public data, and ships with the code, the maps, and a writeup of what I did and what I got stuck on.

Everything was done locally on my own machine. No managed cloud services, no paid APIs.

## The ten projects

| # | Project | Question it answers | Live map |
|---|---|---|---|
| **1** | [InSAR Road Subsidence — Delhi](01-insar-road-subsidence/) | Is this stretch of road sinking, and by how much? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/01-insar-road-subsidence/) |
| **2** | [Café Location Intelligence — Tbilisi](02-real-estate-intel/) | Where in Tbilisi should I open a café? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/02-real-estate-intel/) |
| **3** | [Delivery Route Optimization — Tbilisi](03-route-optimization/) | Given 60 stops and 5 vans, what's the fastest set of routes? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/03-route-optimization/) |
| **4** | [Jakarta Compound Flood Risk](04-flood-risk/) | If Jakarta floods tomorrow, which schools and hospitals are exposed? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/04-flood-risk/) |
| **5** | [Web GIS Dashboard — Delhi PS](05-web-gis-dashboard/) | Let a non-technical stakeholder explore the data themselves | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/05-web-gis-dashboard/) |
| **6** | [GeoAI Road Damage Detection](06-geoai-road-damage/) | Can a model spot potholes in dashcam frames and georeference them? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/06-geoai-road-damage/) |
| **7** | [Sentinel-2 LULC Classification — Bengaluru](07-lulc-classification/) | How much of Bengaluru's bare soil and vegetation became built-up between 2020 and 2024? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/07-lulc-classification/) |
| **8** | [15-Minute City — Paris](08-15min-city/) | What fraction of Paris can reach all six daily essentials in a 15-minute walk? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/08-15min-city/) |
| **9** | [NDVI Deforestation — Rondônia](09-ndvi-change/) | When did each forest pixel along BR-364 get cleared, and does the political cycle show up? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/09-ndvi-change/) |
| **10** | [H3 Mobility — NYC Yellow Taxi](10-h3-mobility/) | Where do NYC pickups and dropoffs concentrate, and how does the pattern shift through the day? | [Dashboard](https://ishunteam-png.github.io/gis-portfolio/10-h3-mobility/) |

Click into each folder for the README, the methodology, the data, and the code.

## What's interesting at the joins

The most useful piece of work isn't in any single project, it's where two of them touch:

- **Project 1 and Project 6.** The InSAR pipeline measures where the ground is sinking. The road-damage model finds where the surface is cracked. Every one of the four demo detections lands within 50 m of a Persistent Scatterer that's already subsiding at −1.3 to −2.0 mm/yr. That's the early-warning loop you actually want.
- **Project 1 and Project 5.** The dashboard is the way a stakeholder who doesn't run Python explores the InSAR data.
- **Project 2 and Project 4** (potential). The café-suitability ranking, but reweighted to exclude cells inside the flood-risk band. One day of work; both pipelines exist.
- **Project 7 and Project 1** (potential). The LULC change map shows which cells went from bare → built between 2020 and 2024. New construction is exactly where you'd expect to see settlement-driven InSAR subsidence start appearing. Run a Bengaluru InSAR pilot, join to the LULC `built_in_2024 = True` polygons, and you get a "houses that are likely to crack" early-warning list.
- **Project 8 and Project 10.** Both measure accessibility, just at different scales — 15-min walk vs. taxi-ride hexes. Together they describe the active-transport vs motorised-transport divide of a city.

## What I used

Python 3.14 with GeoPandas, Rasterio, Shapely, scipy.ndimage, NetworkX, OSMnx, OR-Tools, ultralytics + PyTorch (CPU) for the YOLO bits, MintPy + SNAP for the InSAR. **h3-py and DuckDB** for the NYC mobility work, **pystac-client + stackstac + scikit-learn** for the LULC pipeline, **Google Earth Engine** Python SDK for the deforestation time series, **alphashape** for the Paris isochrones. Leaflet + Chroma.js on the front end. Matplotlib for the static figures. Folium for the interactive HTML when I didn't need a custom dashboard.

No proprietary software anywhere. All the data is from open sources: Sentinel-1 via ASF Vertex, Sentinel-2 via Element84 Earth Search, Landsat via Earth Engine, OpenStreetMap via Overpass, Mapzen terrain tiles, ERA5 atmospheric reanalysis, Wikimedia Commons for the pothole images, NYC TLC for the taxi records, HuggingFace for the pre-trained YOLO weights.

## Contact

singhishu2060@gmail.com
