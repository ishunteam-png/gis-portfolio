# Project 6 — GeoAI Road Damage Detection

A pre-trained YOLOv8 segmentation model running on real pothole photos, plus a georeferencing wrapper, plus a join back to Project 1's InSAR Persistent Scatterers. The point of the join is to test the hypothesis that surface damage co-locates with subsiding ground.

![Annotated detection grid — 4 pothole images](assets/detections_grid.png)

## How it works

- Pre-trained YOLOv8m-seg pothole model (55 MB, public, single class) from HuggingFace.
- Inference on 4 real pothole photos pulled from Wikimedia Commons.
- For each detection: bounding box + confidence + pixel-level segmentation mask.
- Severity computed from the **mask** area, not the bbox area. (A box always overestimates the actual damaged surface because it has to enclose the irregular shape, so it includes a lot of intact pavement.)
- Geolocation from EXIF GPS if the image has it, otherwise from a synthetic dashcam route through the Delhi AOI.
- For each detection, find the nearest Project 1 Persistent Scatterer and record its vertical velocity.

Result: **all four detections land within ~50 m of a PS that's subsiding at −1.3 to −2.0 mm/yr.** With four images that's anecdotal, not proof. But it demonstrates the pipeline works end-to-end — satellite imagery → InSAR → PS dataset → spatial join → ranked output.

## The cross-project tie-in

![PS join — detection vs nearest PS V_U](assets/ps_join.png)

Each bar is one detection. The value is the vertical velocity of the *nearest Persistent Scatterer* to that detection's geolocation. All four bars are negative (sinking ground), red bars are ≤ −2 mm/yr.

Why it matters operationally: if a city DOT runs both an InSAR programme (Project 1) and a dashcam-AI programme (this one), the *join* is the early-warning loop. **Subsurface motion shows up months to years before surface damage.** So the InSAR programme flags hotspots → the dashcam programme patrols them → confirmed surface damage triggers a maintenance budget request. The two pipelines plus the join is what operationalises Béjar-Pizarro et al. 2017 (which showed the same effect in Lorca, Spain, with 1–3 year lead time).

![Detections overlaid on the Delhi PS cloud](assets/detections_map.png)

Detections (X markers) over the same Delhi PS cloud, colour-coded by V_U. The dashed line is the synthetic dashcam route through the AOI.

## Why mask-area severity beats bbox-area

With the same 4 detections, the two severity heuristics disagree pretty hard:

| Detection | bbox-area severity (legacy) | mask-area severity (current) |
|---|:--|:--|
| pothole_03 (conf 0.41) | "severe" | **minor** |
| pothole_03 (conf 0.27) | "severe" | **minor** |
| pothole_04 (conf 0.62) | "severe" | **moderate** |
| pothole_04 (conf 0.27) | "minor" | **minor** |

The mask-based version is more conservative and more honest. Three detections the bbox thought were "severe" turn out to be low-area damages where most of the box was intact pavement around a small irregular crater. One genuine moderate damage stays moderate. This is the kind of correction that takes the pipeline from "works in a demo" to "something a maintenance team would trust the numbers from".

## The interactive map

The [dashboard for this project](https://ishunteam-png.github.io/gis-portfolio/06-geoai-road-damage/) shows the detections on the Delhi PS cloud, with each detection's nearest-PS V_U visible on hover.

## What I'd do next

The single-class limitation is the big one. RDD2022 is a public road-damage dataset with longitudinal cracks, transverse cracks, alligator cracks, potholes, and repair patches. A fine-tune on that gives a real damage taxonomy, which is what you actually need for a maintenance backlog.

Then multi-frame de-duplication. A real dashcam observes the same pothole in many consecutive frames; without clustering, the same physical defect counts 10–20 times in the output GeoJSON. DBSCAN on (lat, lon, t) collapses them.

Real-cm² severity via camera calibration. The geometric mask-area-fraction I'm using is dimensionless. With camera intrinsics (focal length, sensor size) and mounting geometry (height above road, angle) you can convert to actual cm² of damaged pavement, which is what drives a repair-cost estimate.

And a proper join: instead of nearest-PS-by-distance, intersect a 50 m disk around each detection with the PS cloud and use the mean V_U of all PS inside. More statistically stable than nearest-only.

## Reference

Béjar-Pizarro et al. (2017) — InSAR-measured subsidence in Lorca predicts surface damage to roads and pipelines with 1–3 year lead time. This project is the pipeline that operationalises that finding, end-to-end, open-source.
