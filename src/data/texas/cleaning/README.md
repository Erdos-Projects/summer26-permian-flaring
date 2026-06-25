# Texas PDQ Data Cleaning Pipeline

This folder contains a sequential pipeline of Jupyter notebooks that extract, clean, and spatially enrich Texas oil production data sourced from the **Railroad Commission of Texas (RRC) Production Data Query (PDQ) Dump**. and **. Well Layers By County**.

**Source:** [RRC Data Sets Available for Download](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/)  
**Raw data:**  PDQ: `summer26-permian-flaring/data/raw/texas/texas_pdq.zip`  and Well Layers By County: `summer26-permian-flaring/data/raw/texas/Wells/texas_pdq.zip`
**Outputs:** `summer26-permian-flaring/data/raw/texas/cleaned_data/`

Note: `summer26-permian-flaring/data/` is not tracked by git

> ⚠️ **The notebooks must be run in the order listed below.** Each notebook depends on output files produced by the one before it.

---

## Pipeline Overview

```
texas_prod_disp_cleaned.ipynb
        │
        ▼  texas_total_prod.parquet
        │  texas_prod_disp.parquet
        │
texas_well_lease_api.ipynb
        │
        ▼  well_api_lease.parquet
        │
texas_lease_level_coordinate_centroid.ipynb
        │
        ▼  lease_well_coordinates.geoparquet
           wells_per_lease.parquet
        │
texas_well_disp_coord.ipynb
        │
        ▼  prod_per_well_approx.parquet
           prod_per_well_approx.geoparquet
```

---

## Background

Texas RRC production data is reported at the **lease level**, not the well level. A single lease may contain multiple wells. This pipeline:

1. Extracts lease-level oil production and disposition data from the PDQ dump.
2. Extracts the well-to-lease mapping and API numbers from well completion records.
3. Joins API numbers to county-level shapefiles to obtain well coordinates, then computes a **centroid per lease** as a spatial proxy.
4. Merges production/disposition data with well coordinates and distributes lease-level volumes equally across all wells in the lease to produce an **approximate well-level dataset**.

The PDQ dump covers oil and gas production from **1993 to the present**, updated monthly. This pipeline filters for **oil leases only** (`OIL_GAS_CODE = "O"`). The gas data included is **casinghead gas (CSGD)** — natural gas co-produced with crude oil — and is not from standalone gas wells.

---

## Notebooks

### 1. `texas_prod_disp_cleaned.ipynb`
**Purpose:** Extract lease-level oil production volumes and disposition breakdowns from the PDQ dump.

**Reads from raw zip:**
- `OG_LEASE_CYCLE_DATA_TABLE.dsv` — monthly production volumes per lease
- `OG_LEASE_CYCLE_DISP_DATA_TABLE.dsv` — how produced oil and gas was disposed of (pipeline, truck, flared, etc.)

**Key processing steps:**
- Filters to oil leases (`OIL_GAS_CODE = "O"`)
- Retains columns for lease identity, production month, oil production volume, casinghead gas volume, operator, and field
- Parses `CYCLE_YEAR_MONTH` (YYYYMM) into a proper `date` column
- Drops rows with no oil production (`LEASE_OIL_PROD_VOL` is null)
- Renames raw disposition code columns to human-readable names (e.g., `LEASE_OIL_DISPCD00_VOL` → `oil_pipeline_bbl`)
- Computes derived columns:
  - `oil_sold_total_bbl` — sum of pipeline + truck + tank car dispositions
  - `total_vented_flared_mcf` — total gas vented or flared
  - `total_gas_to_processing_mcf` — total gas sent to processing plant
- Drops rows with no oil sold (`oil_sold_total_bbl` is null)

**Outputs:**
| File | Description |
|------|-------------|
| `texas_total_prod.parquet` | Lease-month production volumes (oil + casinghead gas) |
| `texas_prod_disp.parquet` | Lease-month disposition breakdown with derived flaring/sales columns |

---

### 2. `texas_well_lease_api.ipynb`
**Purpose:** Extract the mapping between wells, leases, and API numbers from the well completion table.

**Reads from raw zip:**
- `OG_WELL_COMPLETION_DATA_TABLE.dsv` — well completion records linking wells to leases and API numbers

**Key processing steps:**
- Filters to oil wells (`OIL_GAS_CODE = "O"`)
- Retains district, lease number, well number, county, wellbore location code, and API components
- Constructs a full 8-digit RRC API number: `API_NO = API_COUNTY_CODE (3 digits) + API_UNIQUE_NO (5 digits)`

**Outputs:**
| File | Description |
|------|-------------|
| `well_api_lease.parquet` | Well-to-lease mapping with 8-digit API numbers; ~587K rows |

---

### 3. `texas_lease_level_coordinate_centroid.ipynb`
**Purpose:** Join API numbers to RRC GIS shapefiles to obtain well coordinates, then compute a centroid coordinate per lease.

**Reads:**
- `cleaned_data/texas_total_prod.parquet`
- `cleaned_data/well_api_lease.parquet`
- `data/raw/texas/Wells/` — 255 county-level shapefile zips from the RRC [Well Layers by County](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/) dataset

**Key processing steps:**
- Constructs a composite `lease_key` (`OIL_GAS_CODE_DISTRICT_NO_LEASE_NO`) to uniquely identify leases across both files
- Normalizes API numbers to the 8-digit RRC format (`API8 = county_3digits + unique_5digits`), handling 8-, 10-, and 12-digit variants
- Reads all 255 county shapefiles, projects coordinates from NAD27 to WGS84 (EPSG:4326), and keeps only point geometries
- Matches well GIS records to the lease/well table on `api8`
- Computes a **centroid** of all well point coordinates within each lease as the lease's spatial representative
- Counts the number of wells with valid coordinates per lease (`n_wells_with_coordinates`)

**Outputs:**
| File | Description |
|------|-------------|
| `lease_well_coordinates.geoparquet` | Per-well coordinates joined to lease keys; geometry in WGS84 |
| `wells_per_lease.parquet` | Count of wells with coordinates per lease, plus centroid lat/lon |

---

### 4. `texas_well_disp_coord.ipynb`
**Purpose:** Combine production/disposition data with well coordinates and distribute lease-level volumes to approximate well-level production.

**Reads:**
- `cleaned_data/texas_prod_disp.parquet`
- `cleaned_data/lease_well_coordinates.geoparquet`
- `cleaned_data/wells_per_lease.parquet`

**Key processing steps:**
- Reconstructs `lease_key` on the production table for joining
- Left-joins production rows to well coordinates on `lease_key` — if a lease has N wells, this creates N rows per month, each carrying the full lease volume
- Merges in `wells_per_lease` to get `n_wells_with_coordinates`
- Drops minor disposition columns to reduce memory footprint
- Divides all production/disposition volume columns by `n_wells_with_coordinates` to distribute the lease volume equally across wells

> ⚠️ **Interpretation note:** The resulting per-well volumes are an equal-split approximation. They do not reflect actual measured per-well production. Use with appropriate caution.

**Retained disposition columns after cleanup:**
- `oil_pipeline_bbl`, `oil_truck_bbl`
- `csgd_field_ops_fuel_mcf`, `csgd_transmission_mcf`, `csgd_processing_plant_mcf`
- `csgd_vented_flared_mcf`, `csgd_gas_lift_mcf`, `csgd_repressure_mcf`
- `oil_sold_total_bbl`, `total_vented_flared_mcf`

**Outputs:**
| File | Description |
|------|-------------|
| `prod_per_well_approx.parquet` | Approximate well-level production/disposition data (no geometry) |
| `prod_per_well_approx.geoparquet` | Same, with point geometry for each well |

---

## Output File Summary

All outputs land in `summer26-permian-flaring/data/raw/texas/cleaned_data/`.

| File | Produced by | Description |
|------|-------------|-------------|
| `texas_total_prod.parquet` | Notebook 1 | Lease-month oil + CSGD production volumes |
| `texas_prod_disp.parquet` | Notebook 1 | Lease-month oil and gas disposition breakdown |
| `well_api_lease.parquet` | Notebook 2 | Well → lease → API number mapping |
| `lease_well_coordinates.geoparquet` | Notebook 3 | Per-well coordinates joined to lease keys |
| `wells_per_lease.parquet` | Notebook 3 | Well count and centroid per lease |
| `prod_per_well_approx.parquet` | Notebook 4 | Approximate well-level production (tabular) |
| `prod_per_well_approx.geoparquet` | Notebook 4 | Approximate well-level production (spatial) |

---

## Output Column Descriptions

### `texas_total_prod.parquet`
Grain: one row per lease per production month. Only leases with at least one barrel of oil production are included.

| Column | Type | Description |
|--------|------|-------------|
| `oil_gas_code` | category | Always `"O"` (oil leases only) |
| `district_no` | category | RRC district number (e.g. `"08"`, `"7B"`) |
| `lease_no` | string | RRC lease number; unique within a district |
| `field_no` | string | 8-digit RRC field number |
| `lease_oil_prod_vol` | float | Oil produced in barrels (BBL); null if zero |
| `lease_csgd_prod_vol` | float | Casinghead gas produced in MCF; null if zero |
| `lease_csgd_tot_disp` | float | Total casinghead gas disposed of in MCF |
| `operator_no` | string | RRC-assigned operator ID |
| `operator_name` | string | Operator name as filed on RRC Form P-5 |
| `date` | datetime | Production month parsed from `CYCLE_YEAR_MONTH` (first day of month) |

---

### `texas_prod_disp.parquet`
Grain: one row per lease per production month. Only leases with a non-null `oil_sold_total_bbl` are included.

**Identity columns**

| Column | Type | Description |
|--------|------|-------------|
| `oil_gas_code` | category | Always `"O"` |
| `district_no` | category | RRC district number |
| `lease_no` | string | RRC lease number |
| `field_no` | string | RRC field number |
| `operator_no` | string | RRC operator ID |
| `operator_name` | string | Operator name |
| `date` | datetime | Production month |

**Oil disposition columns** (units: BBL)

| Column | Source code | Description |
|--------|-------------|-------------|
| `oil_pipeline_bbl` | `DISPCD00` | Oil moved off lease by pipeline |
| `oil_truck_bbl` | `DISPCD01` | Oil moved off lease by truck |
| `oil_tankcar_bbl` | `DISPCD02` | Oil moved off lease by tank car or barge |
| `oil_tank_cleaning_bbl` | `DISPCD03` | Net oil recovered during tank cleaning |
| `oil_circulating_bbl` | `DISPCD04` | Oil used for circulating purposes |
| `oil_lost_stolen_bbl` | `DISPCD05` | Oil lost or stolen |
| `oil_bsw_repressure_bbl` | `DISPCD06` | BS&W from tank cleaning used in repressure |
| `oil_legacy_bbl` | `DISPCD07` | Legacy catch-all code (not used in current system) |
| `oil_skimmed_bbl` | `DISPCD08` | Oil allocated back from Form P-18 (skim oil) |
| `oil_scrubber_bbl` | `DISPCD09` | Oil attributed to scrubber (not used) |
| `oil_no_disp_code_bbl` | `DISPCD99` | Oil reported without a disposition code |

**Casinghead gas (CSGD) disposition columns** (units: MCF)

| Column | Source code | Description |
|--------|-------------|-------------|
| `csgd_field_ops_fuel_mcf` | `DISPCDE01` | Gas used for field operations / lease drilling / compressor fuel |
| `csgd_transmission_mcf` | `DISPCDE02` | Gas delivered directly to a transmission line |
| `csgd_processing_plant_mcf` | `DISPCDE03` | Gas sent to a processing plant |
| `csgd_vented_flared_mcf` | `DISPCDE04` | Gas vented or flared |
| `csgd_gas_lift_mcf` | `DISPCDE05` | Gas used directly for gas lift |
| `csgd_repressure_mcf` | `DISPCDE06` | Gas used for repressure / pressure maintenance |
| `csgd_carbon_black_mcf` | `DISPCDE07` | Gas sent to a carbon black plant |
| `csgd_underground_storage_mcf` | `DISPCDE08` | Gas injected into underground storage |
| `csgd_no_disp_code_mcf` | `DISPCDE99` | Gas reported without a disposition code |

**Derived columns**

| Column | Units | Description |
|--------|-------|-------------|
| `oil_sold_total_bbl` | BBL | Sum of pipeline + truck + tank car oil dispositions |
| `total_vented_flared_mcf` | MCF | Sum of gas well gas + casinghead gas vented or flared |
| `total_gas_to_processing_mcf` | MCF | Sum of gas well gas + casinghead gas sent to processing plant |

---

### `well_api_lease.parquet`
Grain: one row per well completion record. Multiple rows per lease (one per well on the lease).

| Column | Type | Description |
|--------|------|-------------|
| `oil_gas_code` | category | Always `"O"` |
| `district_no` | category | RRC district number |
| `lease_no` | string | RRC lease number |
| `well_no` | string | Well number; unique within a lease |
| `api_county_code` | string | 3-digit RRC/API county code |
| `api_unique_no` | string | 5-digit API unique well number |
| `county_name` | string | County name |
| `wellbore_location_code` | category | Location type: `L` (land), `O` (offshore), `I` (inland waterway), `B` (bay/estuary) |
| `api_no` | string | Full 8-digit RRC API number: `API_COUNTY_CODE (3 digits) + API_UNIQUE_NO (5 digits)` |

---

### `lease_well_coordinates.geoparquet`
Grain: one row per well, with point geometry in WGS84 (EPSG:4326). Contains all columns from `well_api_lease.parquet` plus the columns below, added by joining to RRC county shapefiles.

| Column | Type | Description |
|--------|------|-------------|
| `lease_key` | string | Composite key: `OIL_GAS_CODE_DISTRICT_NO_LEASE_NO` |
| `api8` | string | Normalized 8-digit API number used to join to GIS shapefiles |
| `longitude` | float | Well surface longitude in decimal degrees (WGS84) |
| `latitude` | float | Well surface latitude in decimal degrees (WGS84) |
| `geometry` | geometry | Point geometry (WGS84, EPSG:4326) |
| `source_zip` | string | Source county shapefile zip filename |
| `source_shp` | string | Source `.shp` filename within the zip |
| `well_layer_type` | string | Layer type from the RRC shapefile (e.g. surface point, bottom hole) |
| `API`, `API10`, `APINUM` | string | Raw API identifier fields from the shapefile, when present |
| `LAT27`, `LONG27` | float | Original NAD27 coordinates from the shapefile, when present |
| `LAT83`, `LONG83` | float | NAD83 coordinates from the shapefile, when present |
| `RELIAB`, `SYMBOL`, `SYMNUM` | string | Shapefile metadata fields, when present |

---

### `wells_per_lease.parquet`
Grain: one row per lease. Used by notebook 4 to distribute lease-level volumes across wells.

| Column | Type | Description |
|--------|------|-------------|
| `lease_key` | string | Composite key: `OIL_GAS_CODE_DISTRICT_NO_LEASE_NO` |
| `n_wells_with_coordinates` | int | Count of distinct API8 numbers with valid coordinates for this lease |
| `lease_latitude` | float | Centroid latitude of all wells in the lease (decimal degrees, WGS84) |
| `lease_longitude` | float | Centroid longitude of all wells in the lease (decimal degrees, WGS84) |

---

### `prod_per_well_approx.parquet` / `prod_per_well_approx.geoparquet`
Grain: one row per well per production month. All volume columns have been divided by `n_wells_with_coordinates`, distributing the lease total equally across wells.

> ⚠️ These are **approximations**. Each well in a lease receives an equal share of lease-level volumes. Actual per-well production is not available in the public RRC data.

**Identity and spatial columns**

| Column | Type | Description |
|--------|------|-------------|
| `date` | datetime | Production month |
| `lease_key` | string | Composite lease identifier |
| `field_no` | string | RRC field number |
| `operator_no` | string | RRC operator ID |
| `operator_name` | string | Operator name |
| `api8` | string | 8-digit API number for the well |
| `well_no` | string | Well number within the lease |
| `county_name` | string | County name |
| `longitude` | float | Well surface longitude (WGS84) |
| `latitude` | float | Well surface latitude (WGS84) |
| `geometry` | geometry | Point geometry — `.geoparquet` only |

**Per-well approximated volume columns** (lease total ÷ `n_wells_with_coordinates`)

| Column | Units | Description |
|--------|-------|-------------|
| `oil_pipeline_bbl` | BBL | Oil moved by pipeline, per well |
| `oil_truck_bbl` | BBL | Oil moved by truck, per well |
| `csgd_field_ops_fuel_mcf` | MCF | Casinghead gas used for field ops fuel, per well |
| `csgd_transmission_mcf` | MCF | Casinghead gas to transmission line, per well |
| `csgd_processing_plant_mcf` | MCF | Casinghead gas to processing plant, per well |
| `csgd_vented_flared_mcf` | MCF | Casinghead gas vented or flared, per well |
| `csgd_gas_lift_mcf` | MCF | Casinghead gas used for gas lift, per well |
| `csgd_repressure_mcf` | MCF | Casinghead gas used for repressure, per well |
| `oil_sold_total_bbl` | BBL | Total oil sold (pipeline + truck + tank car), per well |
| `total_vented_flared_mcf` | MCF | Total gas vented or flared (all sources), per well |

---

## Data Source Reference

The PDQ dump is a full export of the RRC's Production Data and Historical Ledger databases. Key tables used in this pipeline:

| Table | Used in | Description |
|-------|---------|-------------|
| `OG_LEASE_CYCLE` | Notebook 1 | Monthly production volumes by lease |
| `OG_LEASE_CYCLE_DISP` | Notebook 1 | Monthly disposition volumes by lease |
| `OG_WELL_COMPLETION` | Notebook 2 | Well completion records with API numbers |

For full column definitions, see the `pdq-dump-user-manual.pdf` included in this folder.

---

## Dependencies

```
pandas
geopandas
pyogrio        # fast shapefile reader (fallback: fiona)
tqdm
pathlib        # standard library
zipfile        # standard library
```

All notebooks use `latin-1` encoding and `}` as the delimiter when reading `.dsv` files from the PDQ zip.