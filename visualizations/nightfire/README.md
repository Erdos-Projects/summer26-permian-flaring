# Permian Flaring — Visualization

Self-contained folder for the VIIRS Nightfire (VNF) flaring visualizations: a static
site map (folium) and a month-by-month flaring-intensity slider / density heatmap (Plotly).
Every input the notebook reads lives in this folder, so nothing depends on paths outside it.

## Folder layout

```
visualization/
├── permian_sites_map.ipynb        # the notebook
├── permian_sites_full.csv         # Permian site catalog        → site-map cells
├── upstream.shp                   # clean polygon geometry       → footprint-polygon layer
├── upstream.shx                   #   shapefile sidecar (index)
├── upstream.dbf                   #   shapefile sidecar (attributes)
├── upstream.prj                   #   shapefile sidecar (projection)
├── upstream.cpg                   #   shapefile sidecar (encoding)
├── monthly_aggregates/            # per-site monthly CSVs        → slider / density cells
│   ├── site_9868_multiyear_vnf_series.csv
│   ├── site_XXXX_multiyear_vnf_series.csv
│   └── …                          # one file per site, original names
└── permian_sites_map.html         # written by the site-map cell (after a run)
```

## Inputs

| File / folder | Used by | Notes |
|---|---|---|
| `permian_sites_full.csv` | site map (folium) | Permian subset with `Catalog ID`, `state`, `in_delaware`, `ID2015…ID2021`. |
| `upstream.shp` (+ `.shx .dbf .prj .cpg`) | site map (folium) | Polygon geometry. **All five files must travel together** — a shapefile is the set, not one file. |
| `monthly_aggregates/` | slider, density heatmap (Plotly) | One CSV per site. Each must carry `flare_id, lat, lon, year_month, rh_sum, n_detect, n_nondet_cm0, n_nondet_cm1`. Produced by `aggregate_vnf_monthly.py`. |

The two halves are independent: the Plotly cells need **only** `monthly_aggregates/`; the
folium cells need the catalog **and** the shapefile set. Drop whichever inputs you don't use.

## Running it

1. Set the path constants in the setup cells to the local copies:
   - `PERMIAN = "permian_sites_full.csv"`
   - `SHP = "upstream.shp"`
   - `AGG_DIR = Path("monthly_aggregates")`
2. Install dependencies:
   ```
   pip install pyshp folium plotly pandas numpy
   ```
   (`import shapefile` comes from **pyshp**, not a package named `shapefile`.)
3. Run top to bottom.

**Outputs:** the folium map saves to `permian_sites_map.html`. The Plotly figures render
**inline only** — add `fig.write_html("flaring_slider.html")` after `fig.show()` to save them.

## Conventions and gotchas

- **Geometry comes from `upstream.shp`, never the CSV.** The `geometry` column in any
  `upstream.csv` is truncated to 254 chars (a DBF text-field limit) and is unusable; the
  shapefile holds the real polygons.
- **Join key is the string `Catalog ID` ↔ `id`**, not the integer `ID` (which is just
  `upstream`'s positional index and breaks if the file is re-sorted). ~2250 of 2254 sites match.
- **The intensity metric is mean radiant heat per clear look (MW):**
  `rh_per_clear_look = rh_sum / (n_detect + n_nondet_cm0 + n_nondet_cm1)`.
  The denominator is the number of cloud-free opportunities to observe (all detections plus
  clear-sky non-detections, cloud mask 0/1), which removes the observation-frequency bias.
- **Missing ≠ zero.** A month with clear looks and no flare is a real `0`. A month with only
  cloudy looks has no information → `NaN`, and is dropped from the maps so it never renders as zero.
- **The slider uses a fixed color range across all frames** (`range_color`). Without it, each
  frame re-normalizes and months stop being comparable — which defeats the point of the slider.
- **The density heatmap is qualitative only.** It fabricates spatial continuity between discrete
  flares, its blob size is set by the `radius` pixel knob (not physics), and it sums weights within
  the kernel — so clustered sites glow regardless of per-site intensity. Use the point map for any
  per-site or NM-vs-TX comparison.
- **`RH` is radiant power (MW), not volume.** It's the right signal for these maps; a
  flaring-per-barrel analysis would instead use the `Flow_Rate`-derived gas volume.

## Keeping the data current

This folder holds **copies** of `monthly_aggregates/` (and the catalog / shapefile), so it is a
*fork* of the pipeline output, not a live reference. Re-running `aggregate_vnf_monthly.py`
updates the source silently while these copies go stale.

- **Ongoing work:** symlink instead of copying so the folder always tracks the source —
  `ln -s ../pipeline/monthly_aggregates monthly_aggregates`.
- **Frozen presentation snapshot:** keep the copy, and re-copy deliberately as a step in your
  refresh routine when you want it updated.
