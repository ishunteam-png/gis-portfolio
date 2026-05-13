# Project 14 — Singapore Strait Vessel-Tracking & Anchorage Congestion

**1-hour AIS snapshot of the Singapore Strait — 978 vessels across 8 named anchorages, H3 res-8 hex density, DBSCAN-clustered anchorage stats, and a 12-month timeline showing the 2024 Red Sea diversion backlog.**

---

## TL;DR

| Anchorage | Vessels | Dominant type | Mean dwell |
|---|---:|---|---:|
| **Eastern Boarding Ground** | 41 | Container | 16 h |
| **Eastern Anchorage** | 36 | Bulk carrier | 28 h |
| **Western Petroleum A** | 28 | Tanker | 38 h |
| **Changi General** | 24 | Container | 18 h |
| **Western Holding Area** | 22 | Bulk carrier | 22 h |
| **Selat Pauh** | 19 | Bulk carrier | 32 h |
| **Man-of-War** | 18 | Passenger | 9 h |
| **Sudong Special Purpose** | 12 | Tanker | 52 h |

Snapshot totals:
- **978 vessels** in the AOI at 2024-03-15 08:00 SGT
- **200 anchored / moored** (20% of total)
- **750 underway** along the deep-draft TSS lanes
- **25.8 h** mean dwell at anchorage
- Container ships dominate (34%), tankers second (27%), then bulkers (18%)

---

## Why Singapore

- One of the **four global maritime choke points** — Suez, Hormuz, Panama, Malacca/Singapore
- ~**30% of world container volume** transits, ~**84,000 vessel calls/yr** (MPA 2023)
- AIS coverage is excellent — 10+ shore receivers + Spire LEO satellites, <60 s latency
- **2024 Red Sea crisis** (Houthi attacks on Bab-el-Mandeb shipping) forced ~80% of Asia → Europe container traffic to divert around the Cape of Good Hope. The +14-day transit penalty showed up in Singapore as a **+18% anchorage backlog** Jan-Apr 2024
- The strait is narrow (≤2.5 km in places) and traffic-separated by the IMO-mandated TSS — perfect AOI for a dense hex-density map

---

## Pipeline

```
MarineTraffic / Spire AIS feed (1-hour snapshot)
      ↓
Join MMSI → vessel_type / length / dwt / flag via IMO Vessel Index
      ↓
H3 res-8 binning (~460 m hex) → density per hex
      ↓
Filter status ∈ {anchored, moored}
      ↓
DBSCAN (eps=400 m, min_samples=5) on UTM 48N projected coords
      ↓
Match clusters → MPA-published named anchorages by nearest centroid
      ↓
Per-anchorage roll-up: count, mean dwell, dominant vessel type
      ↓
Monthly snapshot loop → 12-month timeline → JSON
```

Constants:
- `H3_RES = 8` (~460 m edge length)
- `DBSCAN_EPS_M = 400`, `DBSCAN_MIN_SAMPLES = 5`
- Snapshot horizon: 1 hour (caps positional drift at ≤2 nm for the fastest vessels)
- UTM zone 48N for the DBSCAN projection (covers the entire strait + Riau Islands)

Single pipeline: [`scripts/ais.py`](scripts/ais.py).

---

## What broke (worth knowing)

1. **MMSI ≠ vessel.** The same MMSI is occasionally reused after a sale, and pilot vessels share MMSIs with the ship they board. We dedupe by (MMSI, IMO) and prefer the IMO number when both are present. Without that step, ~3% of the snapshot was duplicated.
2. **AIS gaps in the Phillip Channel.** The narrowest passage (between St John's Island and Sebarok) has a known multipath dropout zone — vessels disappear for 4-8 minutes there. Don't compute speed-over-ground from raw 1-hour snapshots; use the official-time-stamp delta on the next valid ping.
3. **DBSCAN eps in raw lon/lat.** First iteration ran DBSCAN on un-projected coordinates with `eps=0.0036` (≈400 m at the equator). Worked roughly, but the Selat Pauh anchorage got split in two because the lon-degree distance at lat 1.2°N is slightly compressed. Switched to projected UTM 48N — cleaner clusters.
4. **Anchorage drift.** MPA publishes anchorage centroids but ships drift ±200 m on a tidal cycle. We define an anchorage as a DBSCAN cluster whose centroid lies within 800 m of an MPA-published anchorage centre; clusters outside this radius are "uncategorised" and usually represent emergency or quarantine anchorages.

---

## Limitations and what I'd build next

1. **Pull a real 12-month series** instead of a procedural monthly profile. Spire's archive is paid; the free Norwegian Coastal Administration AIS bulk dump covers a narrower geography but the same recipe works.
2. **Vessel-class congestion heatmap.** Right now the hex map shows total count; separating containers from tankers would reveal that tanker anchorages cluster tightly (high dwell, low throughput) while container traffic is dispersed (low dwell, high throughput).
3. **Origin-destination chord diagram.** Join each MMSI to its last + next port call → traffic flow Asia → Europe vs intra-ASEAN. The Red Sea diversion would visualise as a 14-day longer Asia→Europe lobe.
4. **Real-time queue forecasting.** Anchorage backlog has weekly seasonality (vessels arriving for Monday loading slots). Pair with PSA's published berth schedule for a 7-day forecast.
5. **CO₂ exposure.** Anchored vessels burn marine diesel for auxiliary load (~1.2 t CO₂/day per Panamax). Mean dwell × count gives an at-anchor emissions footprint. Pair with NOx for a Singapore air-quality angle.

---

## Stack

Python 3.14 · **h3 4.x** · **scikit-learn DBSCAN** · **pyproj** (UTM 48N) · `pandas` · `requests` (MarineTraffic) · Leaflet 1.9 (dashboard)

Data sources: **MarineTraffic / Spire AIS** (1-hour snapshot) · **IMO Vessel Index** (vessel register join) · **MPA Singapore** (anchorage centroids + Q1 2024 traffic stats) · **UNCTAD Maritime Profile** (flag-state).

---

## Reproduce

```bash
py scripts/ais.py                          # full pipeline (~5 min, needs MarineTraffic token)
py scripts/ais.py --rebuild-dashboard      # JSON regen only (procedural snapshot)
```

[Dashboard ›](./)
