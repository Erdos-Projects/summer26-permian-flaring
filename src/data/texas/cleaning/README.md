# Texas RRC Oil Production Data Pipeline

This folder contains Jupyter notebooks that extract, clean, and geo-locate oil production data from the Texas Railroad Commission (RRC) Production Data Query (PDQ) dump. The notebooks must be run **in the order listed below**, as each notebook depends on outputs from the previous one.

---

## Data Source

**Texas Railroad Commission — [Data Sets Available for Download](https://www.rrc.texas.gov/resource-center/research/data-sets-available-for-download/)**

Two raw datasets are used:

| Dataset | Local Path |
|---|---|
| Production Data Query (PDQ) dump | `summer26-permian-flaring/data/raw/texas/texas_pdq.zip` |
| Well Layers By County (shapefiles) | `summer26-permian-flaring/data/raw/texas/Wells/` |

The PDQ dump is a complete export of the RRC's production and historical ledger databases, covering **1993 to present**, updated monthly. It is delivered as a nested zip: `texas_pdq.zip` → `PDQ_DSV.zip` → individual `.dsv` files delimited by `}`. Raw data is large (>25 GB uncompressed; ~5 GB compressed). The Well Layers By County dataset contains 255 per-county zip files, each holding shapefiles with well location geometry.

---

## Output Directory

All cleaned outputs are saved to:

```
summer26-permian-flaring/data/raw/texas/cleaned_data/
```

Permian Basin subsets are saved to:

```
summer26-permian-flaring/data/raw/texas/cleaned_data/permian_only/
```

---

## Notebook Execution Order

### 1. `texas_prod_disp_cleaned.ipynb` — Production & Disposition Data

**Purpose:** Extracts oil production volumes and oil/gas disposition breakdowns for every oil lease in Texas from 1993 to present. This is the primary production dataset.

**Source tables inside `PDQ_DSV.zip`:**
- `OG_LEASE_CYCLE_DATA_TABLE.dsv` — monthly lease-level production volumes
- `OG_LEASE_CYCLE_DISP_DATA_TABLE.dsv` — how produced oil and casinghead gas were disposed of

**Key decisions:**
- Filters to **oil leases only** (`OIL_GAS_CODE == "O"`). Gas production captured here is casinghead gas (gas dissolved in crude oil and produced alongside it), not gas from gas wells.
- Texas RRC data is **lease-level only** — there is no public well-level production. One lease may contain multiple wells.
- Rows with no oil production volume (`LEASE_OIL_PROD_VOL` is null or zero) are dropped.
- A `date` column (datetime) is derived from `CYCLE_YEAR_MONTH`.

**Outputs:**

| File | Description |
|---|---|
| `texas_total_prod.parquet` | Monthly oil production and casinghead gas production per lease |
| `texas_prod_disp.parquet` | Monthly oil and casinghead gas disposition breakdown per lease |

---

### 2. `texas_well_lease_api.ipynb` — Well–Lease–API Linkage

**Purpose:** Extracts the mapping between wells and leases, along with each well's 8-digit API number. This is needed to look up well coordinates from the shapefile data.

**Source table inside `PDQ_DSV.zip`:**
- `OG_WELL_COMPLETION_DATA_TABLE.dsv` — one row per well, with its lease number, district, and API county/unique code components

**Key decisions:**
- Filters to oil wells only (`OIL_GAS_CODE == "O"`).
- Constructs the 8-digit RRC API number (`API_NO`) by zero-padding and concatenating `API_COUNTY_CODE` (3 digits) and `API_UNIQUE_NO` (5 digits). This API8 format matches the RRC's well shapefile data.

**Output:**

| File | Description |
|---|---|
| `well_api_lease.parquet` | ~587k rows linking each oil well to its lease and district, with API8 identifier |

---

### 3. `texas_lease_level_coordinate_centroid.ipynb` — Coordinate Assignment

**Purpose:** Joins each well's API number to its geographic coordinates (from RRC shapefiles), then computes a **centroid of all wells per lease** to assign a single representative location to each lease. Also joins these lease centroids to the total production data.

**Source files:**
- `cleaned_data/texas_total_prod.parquet` (from Step 1)
- `cleaned_data/well_api_lease.parquet` (from Step 2)
- `data/raw/texas/Wells/*.zip` — 255 per-county zipped shapefiles from the RRC Well Layers By County dataset

**Key decisions:**
- Shapefiles are in NAD27 (EPSG:4267); all geometries are reprojected to WGS84 (EPSG:4326).
- Only **Point and MultiPoint** geometries are retained (surface and unknown layer types preferred over bottom-hole locations).
- A **stable lease key** (`oil_gas_code_norm + "_" + district_no_norm + "_" + lease_no_norm`) is constructed to join production and well data consistently across files.
- The centroid is computed in Texas Centric Albers projection (EPSG:3083) for accuracy, then converted back to WGS84 lon/lat.
- Because one lease may have multiple wells, joining production to individual wells would duplicate production rows. The centroid approach provides a single spatial anchor per lease without inflating production volumes.

**Outputs:**

| File | Description |
|---|---|
| `lease_well_coordinates.parquet` | All wells with their API8, lease key, and individual coordinates (flat) |
| `lease_well_coordinates.geoparquet` | Same, with geometry column (GeoParquet format) |
| `wells_per_lease.parquet` | One row per lease: lease key, well count, centroid latitude/longitude |
| `tot_prod_with_lease_coord.parquet` | Total production joined to lease centroid coordinates (flat) |
| `tot_prod_with_lease_coord.geoparquet` | Same, with geometry column (GeoParquet format) |

---

### 4. `texas_well_disp_coord.ipynb` — Well-Approximated Disposition Data with Coordinates

**Purpose:** Combines oil/gas disposition data with well coordinates to produce an **approximate well-level dataset**. Since Texas does not publish well-level production, each lease's production is divided equally among its wells to create a per-well proxy.

**Source files:**
- `cleaned_data/texas_prod_disp.parquet` (from Step 1)
- `cleaned_data/lease_well_coordinates.geoparquet` (from Step 3)
- `cleaned_data/wells_per_lease.parquet` (from Step 3)

**Key decisions:**
- Data is filtered to records **after 2011-01-01** to focus on recent production.
- Each well in a lease is assigned the full lease geometry point from the well shapefile (not the centroid). This means one lease-month row becomes N rows, one per well.
- All production/disposition volumes are then **divided by the number of wells with coordinates** (`n_wells_with_coordinates`) to create the per-well approximation.
- ⚠️ **Important caveat:** This equal-split assumption is a simplification. Individual wells within a lease may produce very different volumes. These outputs should be treated as spatial proxies, not precise well-level measurements.

**Outputs:**

| File | Description |
|---|---|
| `prod_per_well_approx.parquet` | Approx. well-level monthly disposition data with lat/lon (flat) |
| `prod_per_well_approx.geoparquet` | Same, with geometry column (GeoParquet format) |

---

### 5. `permian_basin.ipynb` — Permian Basin Subset

**Purpose:** Filters all four cleaned datasets to the **Permian Basin geographic bounding box** and exports as CSV for downstream analysis.

**Source files** (all from `cleaned_data/`):
- `lease_well_coordinates.geoparquet`
- `wells_per_lease.parquet`
- `tot_prod_with_lease_coord.geoparquet`
- `prod_per_well_approx.geoparquet`

**Bounding box used:**

| Bound | Value |
|---|---|
| Latitude min | 29.462935° N |
| Latitude max | 34.021515° N |
| Longitude min | −105.21988° W |
| Longitude max | −100.036107° W |

**Outputs** (all in `cleaned_data/permian_only/`):

| File | Description |
|---|---|
| `permian_wells_with_locn_and_id.csv` | Individual wells in the Permian with coordinates and lease key |
| `permian_wells_per_lease.csv` | Lease-level well counts and centroid coordinates, Permian only |
| `permian_tot_prod_with_lease_coord.csv` | Total monthly production with lease centroids, Permian only |
| `permian_prod_per_well_approx.csv` | Approx. well-level monthly disposition data, Permian only |
| `permian_prod_per_well_approx_small.csv` | Same, with minor non-essential columns dropped |

---

## Column Definitions

### `texas_total_prod.parquet`

| Column | Type | Description |
|---|---|---|
| `oil_gas_code` | category | Always `"O"` (oil leases only in this dataset) |
| `district_no` | category | RRC district number (e.g., `"08"`). The 14 RRC districts are numbered 01–06, 6E, 7B, 7C, 08, 8A, 09, 10. |
| `lease_no` | str | RRC-assigned lease number, unique within a district |
| `field_no` | str | 8-digit RRC field number (first 5 digits identify the field, last 3 identify the reservoir) |
| `lease_oil_prod_vol` | float | Oil produced in **barrels (BBL)** for the month, as reported by the operator |
| `lease_csgd_prod_vol` | float | Casinghead gas produced in **MCF** for the month. Casinghead gas is natural gas dissolved in crude oil and produced alongside it |
| `lease_csgd_tot_disp` | float | Total casinghead gas disposed of in **MCF** (sum of all disposition codes) |
| `operator_no` | str | RRC-assigned operator ID number |
| `operator_name` | str | Operator name as filed on RRC Form P-5 |
| `date` | datetime | Production month (first day of the month; derived from `CYCLE_YEAR_MONTH`) |
| `lease_key` | str | Constructed stable identifier: `{oil_gas_code}_{district_no}_{lease_no}` (e.g., `O_08_00277`). Used to join across all pipeline files. |

---

### `texas_prod_disp.parquet`

Contains the same key/identifier columns as above plus the following disposition breakdowns. Oil volumes are in **BBL**; casinghead gas volumes are in **MCF**.

**Key/identifier columns:**

| Column | Description |
|---|---|
| `oil_gas_code` | Always `"O"` |
| `district_no` | RRC district number |
| `lease_no` | RRC lease number |
| `field_no` | RRC field number |
| `operator_no` | RRC operator ID |
| `operator_name` | Operator name |
| `date` | Production month (datetime) |
| `lease_key` | Stable join key (see above) |

**Oil disposition columns (BBL):**

| Column | Description |
|---|---|
| `oil_pipeline_bbl` | Oil transferred off-lease by **pipeline** |
| `oil_truck_bbl` | Oil transferred off-lease by **truck** |
| `oil_tankcar_bbl` | Oil transferred off-lease by **tank car or barge** |
| `oil_tank_cleaning_bbl` | Net oil recovered during **tank cleaning** |
| `oil_circulating_bbl` | Oil used for **lease circulating purposes** |
| `oil_lost_stolen_bbl` | Oil **lost or stolen** (Form H-8 required if > 5 BBL) |
| `oil_bsw_repressure_bbl` | BS&W from tank cleaning used in **repressure/pressure maintenance** |
| `oil_legacy_bbl` | Legacy code for oil not fitting another category (not used in current system) |
| `oil_skimmed_bbl` | Oil allocated back from Form P-18 (**skim oil**) |
| `oil_scrubber_bbl` | Oil attributed to the lease for **scrubber oil** (legacy; not used) |
| `oil_no_disp_code_bbl` | Oil reported **without a disposition code** |
| `oil_sold_total_bbl` | **Derived:** sum of `oil_pipeline_bbl + oil_truck_bbl + oil_tankcar_bbl` — total oil moved off-lease (proxy for sales volume) |

**Casinghead gas disposition columns (MCF):**

| Column | Description |
|---|---|
| `csgd_field_ops_fuel_mcf` | Casinghead gas used for **field operations** (lease drilling fuel, compressor fuel, etc.) |
| `csgd_transmission_mcf` | Casinghead gas delivered to a **transmission line** (not processed further) |
| `csgd_processing_plant_mcf` | Casinghead gas sent to a **processing plant** |
| `csgd_vented_flared_mcf` | Casinghead gas **vented or flared** |
| `csgd_gas_lift_mcf` | Casinghead gas used for **gas lift** |
| `csgd_repressure_mcf` | Casinghead gas used for **repressure or pressure maintenance** |
| `csgd_carbon_black_mcf` | Casinghead gas sent to a **carbon black plant** |
| `csgd_underground_storage_mcf` | Casinghead gas injected into **underground storage** |
| `csgd_no_disp_code_mcf` | Casinghead gas reported **without a disposition code** |
| `total_vented_flared_mcf` | **Derived:** casinghead gas vented or flared (equals `csgd_vented_flared_mcf` for oil leases; would include gas well flaring if gas leases were included) |
| `total_gas_to_processing_mcf` | **Derived:** total gas sent to processing plant (equals `csgd_processing_plant_mcf` for oil leases) |

---

### `well_api_lease.parquet`

| Column | Type | Description |
|---|---|---|
| `oil_gas_code` | category | Always `"O"` |
| `district_no` | category | RRC district number |
| `lease_no` | str | RRC lease number |
| `well_no` | str | Well number, unique within a lease |
| `api_county_code` | str | 3-digit RRC/API county code identifying the county where the well is located |
| `api_unique_no` | str | 5-digit unique number assigned by the RRC to identify this wellbore |
| `county_name` | str | Name of the county |
| `wellbore_location_code` | category | Surface location of the wellbore: `L` = Land, `O` = Offshore, `I` = Inland Waterway, `B` = Bay/Estuary |
| `api_no` | str | Constructed 8-digit RRC API number (`api_county_code` zero-padded to 3 digits + `api_unique_no` zero-padded to 5 digits). Matches the API8 format used in the RRC well shapefiles. |

---

### `lease_well_coordinates.parquet` / `.geoparquet`

Contains all columns from `well_api_lease.parquet` plus:

| Column | Type | Description |
|---|---|---|
| `oil_gas_code_norm` | str | Normalized oil/gas code (uppercase, stripped) |
| `district_no_norm` | str | Normalized district number (zero-padded to 2 digits for numeric districts; alpha-numeric districts like `8A`, `7B` left as-is) |
| `lease_no_norm` | str | Normalized lease number (zero-padded to 5 digits) |
| `lease_key` | str | Stable join key: `{oil_gas_code_norm}_{district_no_norm}_{lease_no_norm}` |
| `api8_from_components` | str | API8 reconstructed from `api_county_code` + `api_unique_no` components |
| `api8_from_api_no` | str | API8 normalized from the `api_no` field |
| `api8` | str | Final API8 (prefers `api8_from_components`; falls back to `api8_from_api_no`) |
| `longitude` | float | Well longitude in WGS84 decimal degrees (from RRC shapefile) |
| `latitude` | float | Well latitude in WGS84 decimal degrees (from RRC shapefile) |
| `SOURCE_ZIP` | str | Source zip filename within the Well Layers dataset |
| `SOURCE_SHP` | str | Source shapefile name within the zip |
| `well_layer_type` | str | Whether the shapefile represents a `surface` or `bottom` wellbore location |
| `LAT27` | float | Original NAD27 latitude from shapefile (before reprojection), if present |
| `LONG27` | float | Original NAD27 longitude from shapefile (before reprojection), if present |
| `LAT83` | float | NAD83 latitude from shapefile, if present |
| `LONG83` | float | NAD83 longitude from shapefile, if present |
| `RELIAB` | str | RRC reliability code for the coordinate, if present |
| `WELLID` | str | RRC internal well ID from shapefile, if present |
| `geometry` | geometry | Point geometry in WGS84 (GeoParquet only) |

---

### `wells_per_lease.parquet`

| Column | Type | Description |
|---|---|---|
| `lease_key` | str | Stable join key |
| `n_wells_with_coordinates` | int | Number of distinct wells on the lease that have a matched coordinate in the shapefile data |
| `lease_latitude` | float | Centroid latitude for the lease (mean of all well coordinates, computed in Albers projection) in WGS84 |
| `lease_longitude` | float | Centroid longitude for the lease in WGS84 |

---

### `tot_prod_with_lease_coord.parquet` / `.geoparquet`

All columns from `texas_total_prod.parquet`, plus:

| Column | Type | Description |
|---|---|---|
| `n_wells_with_coordinates` | int | Number of wells on the lease with matched coordinates |
| `county_name` | str | County name (from well data, joined via lease key) |
| `lease_longitude` | float | Lease centroid longitude (WGS84) |
| `lease_latitude` | float | Lease centroid latitude (WGS84) |
| `geometry` | geometry | Centroid point geometry in WGS84 (GeoParquet only) |

---

### `prod_per_well_approx.parquet` / `.geoparquet`

All oil and casinghead gas disposition columns from `texas_prod_disp.parquet`, but with volumes **divided by `n_wells_with_coordinates`** to produce per-well approximations, plus:

| Column | Type | Description |
|---|---|---|
| `lease_key` | str | Stable join key |
| `date` | datetime | Production month |
| `api8` | str | 8-digit API number identifying the individual well |
| `well_no` | str | Well number within the lease |
| `county_name` | str | County name |
| `longitude` | float | Individual well longitude (WGS84) — this is the well's own surface location, not the lease centroid |
| `latitude` | float | Individual well latitude (WGS84) |
| `geometry` | geometry | Point geometry in WGS84 (GeoParquet only) |

> ⚠️ **All production/disposition volume columns in this file are approximate per-well estimates.** They are computed by dividing the lease-level monthly volume equally across the number of wells with known coordinates. Wells on the same lease in the same month will have identical volume values. This is a spatial proxy, not a measured per-well production figure.

---

### Permian Basin Output Files (`permian_only/`)

These files contain the same columns as their Texas-wide counterparts (described above), filtered to wells and leases whose coordinates fall within the Permian Basin bounding box. They are saved as **CSV** instead of Parquet. GeoParquet files with geometry columns have an additional `geometry_wkt` column containing the geometry in Well-Known Text (WKT) string format (since CSVs cannot store native geometry objects).

| File | Source dataset |
|---|---|
| `permian_wells_with_locn_and_id.csv` | `lease_well_coordinates.geoparquet` |
| `permian_wells_per_lease.csv` | `wells_per_lease.parquet` |
| `permian_tot_prod_with_lease_coord.csv` | `tot_prod_with_lease_coord.geoparquet` |
| `permian_prod_per_well_approx.csv` | `prod_per_well_approx.geoparquet` |
| `permian_prod_per_well_approx_small.csv` | Same as above, with `field_no`, `operator_name`, `well_no`, `county_name`, and `geometry` columns dropped |

---

## Data Caveats

- **Lease-level granularity:** Texas RRC public data tracks production at the lease level. Individual well volumes are not reported. All "per-well" figures in this pipeline are equal-split approximations.
- **Coordinate match rate:** Not all wells in the PDQ completion table have a matching entry in the well shapefile dataset. Wells without coordinates are excluded from spatial outputs.
- **Oil only:** This pipeline intentionally filters to oil leases (`OIL_GAS_CODE == "O"`). Gas from gas wells is not included. The casinghead gas captured here is co-produced gas from oil operations.
- **Date coverage:** The PDQ dataset covers 1993 to present. The `prod_per_well_approx` outputs are filtered to post-2011 data.
- **Lease key joins:** The `lease_key` field is the primary join key across all files. It normalizes and concatenates `oil_gas_code`, `district_no`, and `lease_no`. Any mismatch in formatting between source tables (e.g., different zero-padding) is handled by the normalization functions in the notebooks.