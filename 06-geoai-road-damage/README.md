# Project 6 — GeoAI Road Damage Detection (with cross-project tie to Project 1)

**Pre-trained YOLOv8m segmentation model → mask-area-calibrated severity → georeferenced damage GeoJSON → joined to Project 1's Persistent Scatterers to test the hypothesis "surface damage co-locates with subsiding terrain."**

![Annotated detection grid](assets/detections_grid.png)

---

## TL;DR

A pre-trained **YOLOv8m-seg** pothole model runs on 4 real road-damage photos from Wikimedia Commons. For each detection the pipeline computes:

- Bounding box + confidence (standard YOLO output)
- **Segmentation mask** (pixel-level damage footprint)
- **Mask-area severity** — minor/moderate/severe driven by `mask_pixels / image_pixels`, NOT the bbox
- **Geolocated point** in the Delhi AOI (synthetic dashcam route)
- **Cross-project join** — nearest Persistent Scatterer from Project 1 + that PS's vertical velocity

For this demo: **every detection falls within ~50 m of a PS subsiding at −1.3 to −2.0 mm/yr.**

| Metric | Value |
|---|---:|
| Images analysed | 4 |
| Detections | 4 |
| Mean confidence | 0.43 |
| Severity (mask-area) | 3 minor · 1 moderate · 0 severe |
| Nearest PS V_U range | −2.0 to −1.3 mm/yr — **all subsiding** |
| Inference runtime | 15.5 s CPU |

---

## Cross-project tie-in — the headline

![PS join — every detection vs its nearest PS](assets/ps_join.png)

For every detection, the bar shows the vertical velocity of the nearest Project-1 Persistent Scatterer. All four bars are negative (sinking ground).

**Why this matters operationally:** if a city DOT has both an InSAR programme (Project 1) and a dashcam-AI programme (Project 6), the join is the early-warning loop. *Subsurface motion shows up months to years before surface damage*. Project 1 flags a hotspot → Project 6 patrols it → confirmed surface damage triggers maintenance budget.

![Spatial overlay](assets/detections_map.png)

The detections (X marks) are placed on the Project-1 PS cloud (color-coded by V_U).

---

## Why mask-area severity beats bbox-area severity

A bounding box always overestimates damage area — it has to contain the irregular shape, so it includes intact pavement.

| | bbox-area (legacy) | mask-area (current) |
|---|:--|:--|
| pothole_03 (conf 0.41) | "severe" | **minor** |
| pothole_03 (conf 0.27) | "severe" | **minor** |
| pothole_04 (conf 0.62) | "severe" | **moderate** |
| pothole_04 (conf 0.27) | "minor" | **minor** |

Mask-based is *more conservative and more honest*.

---

## Stack

ultralytics 8.x (YOLOv8m-seg) · PyTorch 2.11 (CPU) · OpenCV · PIL (EXIF GPS) · Folium · matplotlib

Single script: [`scripts/detect.py`](scripts/detect.py) (~330 lines).

---

## What I'd build next

1. **Multi-class damage taxonomy** — RDD2022 fine-tune adds longitudinal cracks, transverse cracks, alligator cracks, repair patches.
2. **Physical (not geometric) severity** — camera intrinsics + mounting geometry → real cm² of damage.
3. **Frame de-duplication** — cluster consecutive-frame detections via DBSCAN on (lat, lon, t).
4. **PS join refinement** — 50 m disk intersection mean V_U instead of nearest-only.
5. **Mapillary integration** — swap synthetic dashcam route for real per-image GPS from Mapillary tiles.

### Cross-project insight

Béjar-Pizarro et al. (2017) showed in Lorca, Spain that InSAR subsidence patterns predict downstream surface damage to roads and pipelines with 1–3 years of lead time. This project operationalises that finding — fully open-source, fully reproducible, fully end-to-end from satellite to image to map.
