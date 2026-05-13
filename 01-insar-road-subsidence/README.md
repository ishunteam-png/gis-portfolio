# Project 1 — InSAR Road Subsidence (Delhi)

I picked a 4 km stretch of Najafgarh Road in southwest Delhi and tried to measure, in millimetres, how much it has sunk over the last three years. Using only public Sentinel-1 satellite imagery and open-source tools running on my own machine.

![Vertical and east-west velocity, side by side](assets/01_velocity_dual_panel.png)

## What this is

The European Ground Motion Service publishes ground-motion maps for the entire EU at single-millimetre precision. Nobody publishes the equivalent for Indian roads. So I built it for one piece of road, following the EGMS methodology end-to-end.

The pipeline runs entirely on a Linux workstation:

- 88 ascending + 77 descending Sentinel-1 SLC bursts pulled from ASF Vertex (free, 3-year window May 2023 → April 2026)
- ESA precise orbit files
- ESD coregistration through ISCE2, then SNAPHU phase unwrapping — 476 interferogram pairs total
- ERA5 atmospheric correction via PyAPS3 (the only Python interface to ERA5 that I could get working — the install broke twice, had to manually patch the cdsapi credentials)
- MintPy SBAS WLS time-series inversion
- ITRF14 reference frame via the Indian-plate Euler pole from Altamimi et al. 2017
- True 2D decomposition: per-pixel 2×2 LOS-to-ENU solve. The north component gets dropped because Sentinel-1's near-polar orbit can't resolve it.
- Strict EGMS-PSI gate at the end (spatial coherence ≥ 0.70 in both stacks)

**Out the other end: 2,555 Persistent Scatterers, vertical velocity ranging from −10.3 to +4.7 mm/yr.**

## What the maps show

![Vertical velocity](assets/02_vertical_velocity.png)

Clear subsidence cluster in the southwest corner (down to −10 mm/yr) and gentle uplift in the upper-right. Both line up with what the literature says about groundwater extraction in this district (Mishra et al. 2022; Lakhanpal et al. 2024).

![East-west velocity, plate-motion-corrected](assets/03_eastwest_velocity.png)

After subtracting the Indian-plate motion (~40 mm/yr eastward in ITRF14), the residual east-west velocity is patchy and near-zero. Which is what you want — a road sitting on rigid crust shouldn't be moving horizontally relative to the plate. If it were, either the decomposition is broken or there's actually weird lateral motion happening, and the latter is rare.

![PS scatter — V_U vs V_E](assets/04_decomposition_scatter.png)

Each dot is one PS. The bulk of the spread sits along the vertical axis, which means the 2D decomposition is well-conditioned and I'm seeing real motion rather than noise from a badly-conditioned 2×2 system.

![Time series at worst-subsiding PS](assets/05_timeseries.png)

3 years of LOS displacement at the single most-subsiding PS, plotted independently for ASC and DSC stacks. Both tracks show monotonic subsidence with consistent slope, no thermal seasonality. That cross-stack agreement is what tells me this isn't an artefact in one direction.

## Quality checks I actually care about

| Metric | Value |
|---|---:|
| Persistent Scatterers (strict EGMS-PSI gate) | 2,555 |
| Mean temporal coherence, ASC and DSC | > 0.90 |
| 2×2 LOS-to-ENU system determinant (mean) | 0.95 |
| ASC / DSC LOS velocity std | 2.3 / 1.7 mm/yr |

The determinant near 0.95 matters most. If ASC and DSC view the AOI from similar angles, the 2D decomposition becomes ill-conditioned and you start seeing inversion noise where there should be real motion. 0.95 is essentially the best you can hope for. I got lucky with the track geometry at this site.

## The interactive map

A 320-PS stratified sample of the dataset is in the [dashboard for this project](https://ishunteam-png.github.io/gis-portfolio/01-insar-road-subsidence/). The polished version of the same map (with filters, presets, split view) is in [Project 5](../05-web-gis-dashboard/).

## What I'd do next

Operational alerting. Schedule the whole pipeline to re-run every time a fresh Sentinel-1 acquisition lands, run anomaly detection on per-PS velocity drift, alert whenever any PS crosses a threshold. The hard part isn't the math, it's getting MintPy to not blow up when a single SLC fails to coregister.

Also, cross-validating against the nearest IGS station's vertical velocity. Right now I trust the ITRF14 reference frame because the math says it's right, but a residual check against a real GNSS station would be the actual proof.

And extending from PS-only to PS-plus-distributed-scatterer SqueeSAR-style inversion, for better coverage in rural and vegetated areas. The pipeline already supports it in principle, I just haven't tuned the parameters.

## References

- Altamimi, Z., Métivier, L., Collilieux, X. (2017). *ITRF2014 plate motion model.* Geophys. J. Int.
- Mishra et al. (2022) — Groundwater-driven subsidence in NCR Delhi.
- Lakhanpal et al. (2024) — InSAR-derived land deformation in Dwarka.
