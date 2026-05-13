"""
Road Damage Detection — YOLOv8 inference + georeferencing + Project 1 PS join
=============================================================================

Run a pre-trained YOLOv8m segmentation model on real pothole images,
compute mask-area severity, geolocate each detection, then join to the
Project 1 Persistent Scatterer dataset to test the hypothesis "surface
damage co-locates with subsiding terrain".

Outputs:
    assets/annotated/<image>.jpg       per-image overlay (boxes + masks)
    assets/detections_grid.png         contact-sheet of all overlays
    assets/detections_map.png          spatial overlay on Project 1 PS cloud
    assets/ps_join.png                 cross-project tie-in chart
    assets/detections_map.html         Folium interactive
    data/detections.geojson            per-instance + PS join attributes
    data/run_summary.json              counts, breakdown, runtime

Run:
    PYTHONIOENCODING=utf-8 py scripts/detect.py
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import cv2
import folium
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ExifTags
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
SAMPLES = DATA / "sample_images"
ANN_DIR = ASSETS / "annotated"
MODELS = ROOT / "models"
ANN_DIR.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

MODEL_PATH = MODELS / "pothole_m_seg.pt"
SEED = 17
random.seed(SEED)

# Synthetic dashcam route THROUGH the Delhi AOI so the PS join is meaningful
DEMO_ROUTE = [
    (28.5731, 77.0260),
    (28.5805, 77.0335),
    (28.5872, 77.0447),
    (28.5958, 77.0540),
    (28.6038, 77.0612),
]
PS_GEOJSON = ROOT.parent / "01-insar-road-subsidence" / "data" / "persistent_scatterers.geojson"


def parse_exif_gps(img_path: Path):
    try:
        img = Image.open(img_path)
        exif = img._getexif()
        if not exif:
            return None
        gps_tag = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), None)
        if gps_tag is None or gps_tag not in exif:
            return None
        gps = exif[gps_tag]
        def to_deg(value, ref):
            d, m, s = value
            deg = float(d) + float(m)/60 + float(s)/3600
            return -deg if ref in ("S", "W") else deg
        lat = to_deg(gps[2], gps[1])
        lon = to_deg(gps[4], gps[3])
        return lat, lon
    except Exception:
        return None


def severity_from_box_area(box_xyxy, img_shape):
    x1, y1, x2, y2 = box_xyxy
    box_area = max(0.0, (x2 - x1) * (y2 - y1))
    frac = box_area / (img_shape[0] * img_shape[1])
    if frac < 0.01:  return "minor"
    if frac < 0.05:  return "moderate"
    return "severe"


def severity_from_mask(mask, img_shape):
    if mask is None or mask.size == 0:
        return "minor", 0.0
    frac = float(mask.sum()) / float(img_shape[0] * img_shape[1])
    if frac < 0.005: lbl = "minor"
    elif frac < 0.03: lbl = "moderate"
    else: lbl = "severe"
    return lbl, frac


def load_ps_index():
    if not PS_GEOJSON.exists():
        return None
    g = json.loads(PS_GEOJSON.read_text())
    lats = np.array([f["geometry"]["coordinates"][1] for f in g["features"]])
    lons = np.array([f["geometry"]["coordinates"][0] for f in g["features"]])
    vus  = np.array([f["properties"]["v_vertical_mm_yr"] for f in g["features"]])
    return lats, lons, vus


def nearest_ps(lat, lon, ps_lats, ps_lons, ps_vus):
    dy = (ps_lats - lat) * 111_320.0
    dx = (ps_lons - lon) * 111_320.0 * np.cos(np.deg2rad(lat))
    d  = np.sqrt(dx * dx + dy * dy)
    k  = int(np.argmin(d))
    return float(d[k]), float(ps_lats[k]), float(ps_lons[k]), float(ps_vus[k])


# 1. Load model
t0 = time.time()
print(f"[1/4] Loading YOLOv8m-seg model from {MODEL_PATH} ...")
model = YOLO(str(MODEL_PATH))
class_names = model.names

# 2. Inference
print("[2/4] Running inference ...")
images = sorted([p for p in SAMPLES.glob("*.jpg")])
ps_index = load_ps_index()
ps_lats, ps_lons, ps_vus = (None, None, None) if ps_index is None else ps_index

all_detections = []
per_image_stats = []
for idx, img_path in enumerate(images, 1):
    img = cv2.imread(str(img_path))
    if img is None:
        continue
    results = model.predict(img, conf=0.25, iou=0.5, verbose=False)
    r = results[0]

    boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else np.zeros((0, 4))
    confs = r.boxes.conf.cpu().numpy() if r.boxes is not None else np.zeros(0)
    cls   = r.boxes.cls.cpu().numpy().astype(int) if r.boxes is not None else np.zeros(0, dtype=int)
    masks = (r.masks.data.cpu().numpy() if r.masks is not None else
             np.zeros((len(boxes), *img.shape[:2])))

    annotated = r.plot()
    cv2.imwrite(str(ANN_DIR / img_path.with_suffix(".jpg").name), annotated)

    gps = parse_exif_gps(img_path)
    if gps is None:
        gps_base = DEMO_ROUTE[idx % len(DEMO_ROUTE)]
        synth = True
    else:
        gps_base = gps
        synth = False

    for j, (b, c, k) in enumerate(zip(boxes, confs, cls)):
        dlat = (random.random() - 0.5) * 8e-5
        dlon = (random.random() - 0.5) * 8e-5
        lat = gps_base[0] + dlat; lon = gps_base[1] + dlon
        mask_j = masks[j] if j < len(masks) else None
        sev_lbl, mask_frac = severity_from_mask(mask_j, img.shape)
        ps_info = {}
        if ps_lats is not None:
            d_m, p_lat, p_lon, v_u = nearest_ps(lat, lon, ps_lats, ps_lons, ps_vus)
            ps_info = {"nearest_ps_dist_m": round(d_m, 1),
                       "nearest_ps_lat":    p_lat,
                       "nearest_ps_lon":    p_lon,
                       "nearest_ps_v_vertical_mm_yr": round(v_u, 3)}
        all_detections.append({
            "image":         img_path.name,
            "class":         class_names[int(k)],
            "confidence":    float(c),
            "bbox_xyxy":     [float(x) for x in b],
            "mask_frac":     round(mask_frac, 4),
            "severity":      sev_lbl,
            "severity_bbox": severity_from_box_area(b, img.shape),
            "lat": lat, "lon": lon,
            "gps_synthetic": synth,
            **ps_info,
        })

    per_image_stats.append({"image": img_path.name, "detections": int(len(boxes)),
                            "img_shape": list(img.shape[:2]),
                            "gps_source": "exif" if not synth else "synthetic_demo_route"})

print(f"      total detections: {len(all_detections)}")

# 3. Visuals
print("[3/4] Building visuals ...")
annotated_files = sorted(ANN_DIR.glob("*.jpg"))
n = len(annotated_files); cols = min(n, 2); rows = (n + cols - 1) // cols
fig, axes = plt.subplots(rows, cols, figsize=(13, 6.5 * rows))
if rows == 1 and cols == 1: axes = np.array([[axes]])
elif rows == 1 or cols == 1: axes = np.array(axes).reshape(rows, cols)
for ax, p in zip(axes.flat, annotated_files):
    img = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
    ax.imshow(img); ax.set_title(p.name, fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
for ax in axes.flat[len(annotated_files):]:
    ax.axis("off")
fig.suptitle(f"YOLOv8m-seg detections · {len(all_detections)} instances", fontsize=12, y=1.0)
plt.tight_layout()
plt.savefig(ASSETS / "detections_grid.png", dpi=120, bbox_inches="tight")
plt.close(fig)

# Folium
center = ([sum(d["lat"] for d in all_detections)/len(all_detections),
           sum(d["lon"] for d in all_detections)/len(all_detections)]
          if all_detections else DEMO_ROUTE[0])
m = folium.Map(location=center, zoom_start=13, tiles="cartodbpositron")
sev_color = {"minor": "#fcae91", "moderate": "#fb6a4a", "severe": "#a50f15"}
for d in all_detections:
    folium.CircleMarker(
        [d["lat"], d["lon"]], radius=6, color="#222", weight=1,
        fill=True, fill_color=sev_color[d["severity"]], fill_opacity=0.9,
        popup=folium.Popup(
            f"<b>{d['class']}</b> ({d['severity']})<br>"
            f"confidence: {d['confidence']:.2f}<br>"
            f"source image: {d['image']}<br>"
            f"GPS: {'EXIF' if not d['gps_synthetic'] else 'synthetic demo route'}",
            max_width=260),
    ).add_to(m)
if any(d["gps_synthetic"] for d in all_detections):
    folium.PolyLine(DEMO_ROUTE, color="#377eb8", weight=2, opacity=0.5,
                    dash_array="6 8",
                    tooltip="demo dashcam route").add_to(m)
m.save(ASSETS / "detections_map.html")

# Static overlay on PS cloud
fig, ax = plt.subplots(figsize=(11, 9))
ax.set_aspect("equal")
if ps_lats is not None:
    sc = ax.scatter(ps_lons, ps_lats, c=ps_vus, cmap="RdYlBu", s=3, alpha=0.55,
                    vmin=-10, vmax=5)
    cb = plt.colorbar(sc, ax=ax, shrink=0.7); cb.set_label("PS V_U (mm/yr)")
sev_levels = ["minor", "moderate", "severe"]
for sev in sev_levels:
    pts = [d for d in all_detections if d["severity"] == sev]
    if not pts: continue
    xs = [p["lon"] for p in pts]; ys = [p["lat"] for p in pts]
    ax.scatter(xs, ys, c=sev_color[sev], s=180, alpha=0.95, edgecolor="black",
               linewidth=1.2, label=f"damage — {sev} ({len(pts)})",
               marker="X", zorder=5)
ax.plot([p[1] for p in DEMO_ROUTE], [p[0] for p in DEMO_ROUTE],
        color="black", linestyle="--", linewidth=1.5, alpha=0.6,
        label="demo dashcam route")
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
ax.set_title(f"Damage detections joined to Project 1 PS cloud · "
             f"{len(all_detections)} damage instances over "
             f"{len(ps_lats) if ps_lats is not None else 0:,} PS")
ax.legend(loc="lower left", fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(ASSETS / "detections_map.png", dpi=140, bbox_inches="tight")
plt.close(fig)

# PS join chart
if ps_lats is not None and any("nearest_ps_v_vertical_mm_yr" in d for d in all_detections):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    rows = sorted(all_detections, key=lambda d: d.get("nearest_ps_v_vertical_mm_yr", 0))
    labels = [f"{d['image']}\n{d['severity']} (conf {d['confidence']:.2f})" for d in rows]
    vus = [d.get("nearest_ps_v_vertical_mm_yr", 0) for d in rows]
    colors = ["#bd0026" if v < -2 else "#fd8d3c" if v < 0 else "#92c5de" for v in vus]
    ax.barh(labels, vus, color=colors, edgecolor="black", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("V_U of nearest Project 1 PS (mm/yr) — negative = subsiding")
    ax.set_title("Cross-project tie-in: damage detections vs nearest Persistent Scatterer")
    plt.tight_layout()
    plt.savefig(ASSETS / "ps_join.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

# 4. Persist
print("[4/4] Writing GeoJSON + summary ...")
geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [d["lon"], d["lat"]]},
            "properties": {k: v for k, v in d.items() if k not in ("lat", "lon")},
        }
        for d in all_detections
    ],
}
(DATA / "detections.geojson").write_text(json.dumps(geojson))

sev_breakdown = {s: sum(1 for d in all_detections if d["severity"] == s)
                 for s in sev_levels}
cls_breakdown = {}
for d in all_detections:
    cls_breakdown[d["class"]] = cls_breakdown.get(d["class"], 0) + 1

summary = {
    "model_path":     str(MODEL_PATH.relative_to(ROOT)),
    "model_classes":  class_names,
    "n_images":       len(images),
    "n_detections":   len(all_detections),
    "per_image":      per_image_stats,
    "by_severity":    sev_breakdown,
    "by_class":       cls_breakdown,
    "mean_confidence": round(
        float(np.mean([d["confidence"] for d in all_detections]))
        if all_detections else 0.0, 3
    ),
    "runtime_seconds": round(time.time() - t0, 1),
}
(DATA / "run_summary.json").write_text(json.dumps(summary, indent=2))
print(f"Done in {summary['runtime_seconds']}s.")
