# Texas RRC / Permian Basin Flaring Data Pipeline

This pipeline builds an approximate, well-level, geolocated oil production and flaring dataset for
the Permian Basin, starting from three independent public data sources: Texas Railroad Commission
(RRC) production records, RRC well-location shapefiles, and a satellite-derived (VIIRS Nightfire)
catalog of combustion/flaring sites. Four notebooks run in sequence, each depending on the outputs of
the one before it.

Every notebook contains much more detailed explanation in its own markdown cells than this README
covers — this document is a map of the whole pipeline; the notebooks are the reference for exactly
how and why each step works.

---

## Pipeline at a glance

| Step | Notebook | Reads | Produces |
|---|---|---|---|
| 1 | `primary_data_and_well_lease_api_extraction.ipynb` | RRC Production Data Query (PDQ) dump | `texas_prod_disp.parquet`, `well_api_lease.parquet` |
| 2 | `well_coordinates_and_well_level_disp.ipynb` | Step 1 outputs + RRC well-location shapefiles | `lease_well_coordinates.parquet`/`.geoparquet`, `wells_per_lease.parquet`, `prod_per_well_approx.parquet`/`.geoparquet` |
| 3 | `permian_basin.ipynb` | Step 2 outputs | `permian_wells_with_locn_and_id.csv`, `permian_wells_per_lease.csv`, `permian_prod_per_well_approx.csv` |
| 4 | `permian_flaring_sites_and_well_assignment.ipynb` | Step 3 outputs + VIIRS Nightfire site catalog | `permian_flaring_sites.csv`, `permian_prod_per_well_with_site_id.csv` |

**Run the notebooks in this order — each one depends on files written by the previous one.**

---

## Folder structure

All notebooks use relative paths of the form `../../../../data/raw/texas/...` — four `../` segments,
because the notebooks themselves live at `src/data/texas/Cleaning/`, four directory levels below the
project root. Adjust the path variables in each notebook's configuration cell if your layout differs.
The expected layout:

```
<project_root>/
├── data/
│   ├── raw/
│   │   └── texas/
│   │       ├── texas_pdq.zip              ← Step 1 input (RRC production dump)
│   │       ├── Wells/                     ← Step 2 input (~255 RRC well-location shapefile zips)
│   │       │   ├── <county_1>.zip
│   │       │   ├── <county_2>.zip
│   │       │   └── ...
│   │       └── shapefiles.zip             ← Step 4 input (VIIRS Nightfire site catalog)
│   └── processed/
│       └── texas/                          ← all pipeline outputs land here
│           ├── texas_prod_disp.parquet
│           ├── well_api_lease.parquet
│           ├── lease_well_coordinates.parquet
│           ├── lease_well_coordinates.geoparquet
│           ├── wells_per_lease.parquet
│           ├── prod_per_well_approx.parquet
│           ├── prod_per_well_approx.geoparquet
│           ├── prod_per_well_approx_checkpoints/   ← Step 2's crash-recovery cache (one file per year)
│           └── permian_only/
│               ├── permian_wells_with_locn_and_id.csv
│               ├── permian_wells_per_lease.csv
│               ├── permian_prod_per_well_approx.csv
│               ├── permian_flaring_sites.csv
│               └── permian_prod_per_well_with_site_id.csv
└── src/
    └── data/
        └── texas/
            └── Cleaning/                    ← notebooks live here (4 levels below project_root)
                ├── primary_data_and_well_lease_api_extraction.ipynb
                ├── well_coordinates_and_well_level_disp.ipynb
                ├── permian_basin.ipynb
                └── permian_flaring_sites_and_well_assignment.ipynb
```

`data/raw/texas/` holds only what you download by hand (Section "Data sources" below) — nothing in
this pipeline ever writes there. Every notebook output lands under `data/processed/texas/` instead.

Note that `data/raw/texas/shapefiles.zip` (a single zip, VIIRS Nightfire combustion-site catalog) and
`data/raw/texas/Wells/` (a folder of ~255 separate RRC well-location zips) are two unrelated data
sources that happen to have similarly generic names — don't confuse them.

---

## Data sources & how to download everything

Three separate downloads are needed before running the full pipeline.

### 1. RRC Production Data Query (PDQ) dump — for Step 1

- **Where:** https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/
- Find the dataset named **"Production Data Query (PDQ)"** (RRC occasionally renames sections of the
  page). Download it — it arrives as a single outer zip, conventionally saved as `texas_pdq.zip`.
- **Do not unzip it.** Inside is a nested zip (`PDQ_DSV.zip`) containing individual `.dsv` files
  (flat text, `}`-delimited, `latin-1` encoded) — Step 1 reads directly out of both zip layers
  in-memory.
- **Size:** ~5 GB compressed, >25 GB uncompressed. Covers 1993–present, updated monthly.
- Place it at `data/raw/texas/texas_pdq.zip`.

### 2. RRC Well Layers by County (shapefiles) — for Step 2

- **Where:** same RRC download page as above → **"Well"** section → **"ArcView Shape File"** link →
  RRC's Managed File Transfer (MFT) portal, which lists one zip per Texas county (roughly 255 zips
  total). Select **all** counties.
  - The [RRC Public GIS Viewer](https://gis.rrc.texas.gov/GISViewer/) is useful for looking up a
    specific county's number and previewing well locations before downloading.
- **Do not unzip the county zips.** Step 2 reads directly out of each one in-memory.
- Each county zip contains several shapefiles: surface well locations, bottom well locations, and
  well arcs/lines (only surface/bottom point locations are used).
- **Format:** ArcView Shapefile (`.shp`/`.shx`/`.dbf`/`.prj`), Geographic projection, decimal degrees,
  **NAD27** datum (Step 2 reprojects to WGS84). Updated roughly twice a week.
- Place all downloaded county zips in `data/raw/texas/Wells/`.

### 3. VIIRS Nightfire multi-year combustion-site catalog — for Step 4

- **Where:** Colorado School of Mines Earth Observation Group (free account required):
  [`VNF_multiyear_by_type_2012-2021_v20220822.zip`](https://eogdata.mines.edu/wwwdata/downloads/VNF_multiyear_bubble/VNF_multiyear_by_type_2012-2021_v20220822.zip)
- The zip bundles one shapefile (`.shp`/`.shx`/`.dbf`/`.prj`) **and** one companion `.csv` per
  combustion-site-type category (`cement`, `coal_mine`, `downstream`, `industrial`, `landfill`,
  `metallurgy`, `sawmill`, `unique`, `unknown`, `upstream`, `volcano`). Two additional categories are
  distributed only as `.kmz` with no attribute table and are skipped.
- **Do not unzip it.** Step 4 reads directly out of the zip in-memory.
- Place it at `data/raw/texas/shapefiles.zip`.

---

## What each notebook does

### Step 1 — `primary_data_and_well_lease_api_extraction.ipynb`

The pipeline's entry point. Reads two tables out of the RRC PDQ dump:

- `OG_LEASE_CYCLE_DISP_DATA_TABLE.dsv` — monthly lease-level oil/casinghead-gas **disposition**
  (where produced oil and gas ended up: sold via pipeline/truck/tank car, flared, used for gas lift,
  etc.). Filtered to oil leases only. Saved as `texas_prod_disp.parquet`.
- `OG_WELL_COMPLETION_DATA_TABLE.dsv` — one row per well, giving its lease number and the components
  of its 8-digit RRC API number (API8). Saved as `well_api_lease.parquet`.

Both tables are streamed through the raw `.dsv` files in fixed-size chunks (rather than loaded whole)
to keep memory manageable given the multi-gigabyte source files. Note this pipeline is scoped to the
*disposition* table only — the companion raw-production-volume table
(`OG_LEASE_CYCLE_DATA_TABLE.dsv`) is intentionally not used anywhere in this pipeline.

### Step 2 — `well_coordinates_and_well_level_disp.ipynb`

Connects the well/lease data to physical coordinates and builds an approximate well-level production
dataset:

- Builds a stable `lease_key` (normalized `oil_gas_code` + `district_no` + `lease_no`) to join
  `well_api_lease.parquet` and `texas_prod_disp.parquet`, and a normalized `api8` to join wells to
  their shapefile coordinates.
- Reads every county's well-location shapefile (from `data/raw/texas/Wells/`), keeps point geometry
  only, prefers surface over bottom-hole locations, and assigns one coordinate per well.
- **Every well keeps its own coordinate — no lease-level centroid is computed.** Instead, each
  lease's monthly disposition volumes are divided equally across every well known to sit on that
  lease, with the well count kept as an explicit `n_wells_with_coordinates` column so the
  approximation is transparent.
- Because joining lease-level production onto well-level coordinates multiplies row count (a lease
  with 5 wells turns 1 row into 5), this step is processed **one calendar year at a time**, with each
  year's result checkpointed to `prod_per_well_approx_checkpoints/` before being combined — if the
  kernel crashes partway through, re-running the cell picks up where it left off instead of
  restarting.
- Restricts the well-level approximation to production dated after `2012-01-01`, aligned with VIIRS
  Nightfire's earliest coverage (Step 4's flaring-site catalog has no detections before 2012, so
  well-level rows earlier than that can never be matched to a site anyway).

### Step 3 — `permian_basin.ipynb`

A pure geographic + column-trimming subset step — no new data is derived. Filters the statewide Step
2 outputs down to a rectangular Permian Basin bounding box (29.462935–34.021515° N,
−105.21988 to −100.036107° W) and keeps only the columns useful for downstream spatial analysis,
dropping raw/intermediate bookkeeping columns (shapefile provenance, redundant API components, etc.).
Since Step 2 no longer produces a lease-centroid file, the per-lease output is derived by checking
which leases have at least one well inside the bounding box, rather than filtering a centroid
coordinate directly.

### Step 4 — `permian_flaring_sites_and_well_assignment.ipynb`

Two parts:

1. **Flaring site catalog:** reads the VIIRS Nightfire zip, restricts every combustion-site category
   to the Permian Basin bounding box (not just `upstream` — a few `downstream`/`industrial`/`unknown`
   sites also fall inside the region), and saves a clean polygon catalog. Reads geometry from each
   category's `.shp` (not its `.csv`, whose WKT text gets silently truncated at 254 characters for
   large polygons) and pulls a handful of extra descriptive columns in from the `.csv`.
2. **Well → site assignment:** spatially tests every unique Permian well (by location) against every
   flaring-site polygon (`predicate="within"`). A well inside a site's polygon is tagged with that
   site's `site_id`; a well inside no polygon gets `site_id = -1`. The result is broadcast back onto
   every well-month row and saved — no production values are altered, only the new `site_id` column
   is added.

All outputs from this notebook, like Step 3, are CSV, saved to `permian_only/`.

---

## Output file reference

### `texas_prod_disp.parquet` (Step 1)

One row per lease per month.

| Column | Description |
|---|---|
| `oil_gas_code` | Always `"O"` (oil leases only) |
| `district_no` | RRC district number |
| `lease_no` | RRC lease number |
| `field_no` | RRC field number |
| `operator_no` | RRC operator ID |
| `operator_name` | Operator name |
| `date` | Production month |
| `oil_pipeline_bbl`, `oil_truck_bbl`, `oil_tankcar_bbl`, `oil_tank_cleaning_bbl`, `oil_circulating_bbl`, `oil_lost_stolen_bbl`, `oil_bsw_repressure_bbl`, `oil_legacy_bbl`, `oil_skimmed_bbl`, `oil_scrubber_bbl`, `oil_no_disp_code_bbl` | Oil disposition breakdown (BBL) |
| `oil_sold_total_bbl` | Derived: pipeline + truck + tank car (BBL) |
| `csgd_field_ops_fuel_mcf`, `csgd_transmission_mcf`, `csgd_processing_plant_mcf`, `csgd_vented_flared_mcf`, `csgd_gas_lift_mcf`, `csgd_repressure_mcf`, `csgd_carbon_black_mcf`, `csgd_underground_storage_mcf`, `csgd_no_disp_code_mcf` | Casinghead gas disposition breakdown (MCF) |
| `total_vented_flared_mcf` | Derived: total gas vented/flared (MCF) |

### `well_api_lease.parquet` (Step 1)

One row per oil well (~587k rows). Columns are uppercase raw RRC names as saved (lowercased when read
back in by Step 2): `OIL_GAS_CODE`, `DISTRICT_NO`, `LEASE_NO`, `WELL_NO`, `API_COUNTY_CODE`,
`API_UNIQUE_NO`, `COUNTY_NAME`, `WELLBORE_LOCATION_CODE`, `API_NO` (constructed 8-digit API number).

### `lease_well_coordinates.parquet` / `.geoparquet` (Step 2)

One row per well, statewide. Carries the well/lease identifiers from `well_api_lease.parquet` plus:
`lease_key` (stable join key), `api8` (normalized 8-digit API), `longitude`/`latitude`, `geometry`
(`.geoparquet` only), and shapefile provenance columns (`SOURCE_ZIP`, `SOURCE_SHP`, `well_layer_type`,
and — when present in the source shapefile — `RELIAB`, `LAT27`/`LONG27`/`LAT83`/`LONG83`, etc.).

### `wells_per_lease.parquet` (Step 2)

One row per lease, statewide: `lease_key`, `n_wells_with_coordinates`. No centroid coordinates are
computed or stored here.

### `prod_per_well_approx.parquet` / `.geoparquet` (Step 2)

One row per well per month, statewide (date-filtered — see Step 2's note above). All of
`texas_prod_disp.parquet`'s disposition/derived columns, equally divided across wells on the same
lease, plus: `lease_key`, `api8`, `well_no`, `county_name`, `longitude`, `latitude`,
`n_wells_with_coordinates`, `geometry` (`.geoparquet` only).

### `permian_wells_with_locn_and_id.csv` (Step 3)

One row per well, Permian only: `lease_key`, `api8`, `well_no`, `county_name`,
`wellbore_location_code`, `longitude`, `latitude`, `geometry_wkt` (point, WKT text).

### `permian_wells_per_lease.csv` (Step 3)

One row per lease, Permian only (leases with ≥1 well inside the bounding box): `lease_key`,
`n_wells_with_coordinates`.

### `permian_prod_per_well_approx.csv` (Step 3)

One row per well per month, Permian only. `operator_no`, `date`, all disposition/derived columns from
`prod_per_well_approx`, `lease_key`, `api8`, `longitude`, `latitude`, `n_wells_with_coordinates`,
`geometry_wkt` (point, WKT text). `field_no`, `operator_name`, `well_no`, and `county_name` are
dropped as not needed downstream.

### `permian_flaring_sites.csv` (Step 4)

One row per combustion/flaring site polygon, Permian only, across every VIIRS site-type category.
`site_id` (stable numeric ID, taken from the source catalog's own row position within its category),
`catalog_id` (full descriptive source ID), `type`, `category`, `country`, `iso`, `latitude`,
`longitude` (site's representative point), `area`, `dist_std`, `cov1`, `n_dtct`, `n_dates`, `t_mean`,
`t_std`, `time_flag`, `id2015`–`id2021` (per-year detection-count columns), `geometry` (polygon
boundary, WKT text — note this column is literally named `geometry`, not `geometry_wkt`, in this one
file). The file also carries a leading, unlabeled index column when opened (an artifact of how it's
saved) — expected, not an error.

### `permian_prod_per_well_with_site_id.csv` (Step 4)

One row per well per month, Permian only — identical to `permian_prod_per_well_approx.csv` with one
added column: `site_id`, the flaring/combustion site whose polygon the well falls inside, or `-1` if
it falls inside none. Since `site_id` depends only on a well's fixed location, every well-month row
for the same well carries the same value.

---

## Key data caveats (apply throughout)

- **Lease-level source data:** RRC production data is only ever reported at the lease level, never
  per well. All "per-well" figures in this pipeline (from Step 2 onward) are equal-split
  approximations across the wells known to sit on a lease, not measured well-level production.
- **Oil leases only:** the pipeline filters to `OIL_GAS_CODE == "O"` throughout. Casinghead gas
  (dissolved in and produced alongside crude oil) is included; gas from dedicated gas wells is not.
- **Coordinate match rate:** not every well in the RRC completion data has a matching shapefile
  coordinate; wells without one are excluded from all spatial outputs.
- **Permian bounding box:** a simple rectangle, not a precise geologic basin boundary — some sites
  near the true boundary may be included or excluded depending on how closely it hugs this rectangle.
