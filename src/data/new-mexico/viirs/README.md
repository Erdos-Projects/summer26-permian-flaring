# Permian Basin Flaring Analysis - Detailed Data Pipeline

A breakdown of the data engineering pipeline designed to process satellite-observed flaring data (VIIRS Nightfire), spatial infrastructure mappings, and reported oil/gas production metrics for the Permian Basin. 

## System & Environment Setup
This pipeline is tailored for automated development environments managed via Zsh, Git, and Conda. For seamless version control synchronization, ensure your workspace initialization scripts implement upstream logic to automatically fetch and pull changes only if a remote origin exists. 

Given the intensive streaming operations required by the Earth Observation Group (EOG) data, the scripts utilize an in-memory processing architecture.

---

## 1. `download_viirs_vnf.py`
**Purpose:** Bulk extraction of daily raw VIIRS Nightfire (VNF) data across the Permian bounding box.

* **Datasets Used:** * EOG VIIRS Nightfire v30 Daily CSVs (`VNF_{sat}_d{date_str}_noaa_v30.csv.gz`).
* **Locations:**
  * **Source:** Fetched remotely from `https://eogdata.mines.edu/wwwdata/viirs_products/vnf/v30/`.
  * **Output Directory:** `~/work/projects/summer26-permian-flaring/data/raw/new-mexico/viirs/`
  * **Output File:** `nm_viirs_vnf_2021_2026.csv`
  * **State Tracker:** `processed_logs.txt`
* **Data Analysis Performed:**
  * **In-Memory Transformation:** Gzip streams are downloaded to a virtual `io.BytesIO` file in RAM and passed directly to Pandas, preventing heavy SSD caching.
  * **Spatial Filtering:** Filters global data strictly to the Permian Basin boundaries (`Lat: 31.9 to 33.6`, `Lon: -105.0 to -102.9`).
  * **Quality Control:** Excludes invalid sensor fills by ensuring relative humidity (`RH`) and blackbody temperature (`Temp_BB`) do not equal `999999`.

---

## 2. `test_viirs_vnf.py`
**Purpose:** Diagnostic smoke test for API connectivity and parsing logic over a minimal 3-day window.

* **Datasets Used:** * EOG VIIRS Nightfire v30 Daily CSVs (Restricted to Jan 1 - Jan 3, 2021).
* **Locations:**
  * **Source:** `https://eogdata.mines.edu/wwwdata/viirs_products/vnf/v30/`
  * **Output Directory:** `~/work/projects/summer26-permian-flaring/data/interim/new-mexico/`
  * **Output File:** `test_viirs_vnf.csv`
* **Data Analysis Performed:**
  * Mirrors the spatial and quality filtering logic of the main downloader to validate that the Permian coordinates and NaN-exclusion rules yield the expected spatial subset before initiating a multi-year run.

---

## 3. `map_infrastructure_to_catalogs.py`
**Purpose:** Spatial intersection mapping local state infrastructure (wells and facilities) to EOG's defined multi-year flaring polygon sites.

* **Datasets Used:**
  * Native EOG Upstream Shapefile Catalog (`upstream.shp`).
  * Pre-processed Wells Spatial Data (`nm_wells_spatial.csv`).
  * Pre-processed Facilities Data (`nm_facilities.csv`).
* **Locations:**
  * **Sources:** * `.../data/raw/new-mexico/viirs/multiyear_catalog/VNF_multiyear_by_type_2012-2021_v20220822/upstream.shp`
    * `.../data/interim/new-mexico/nm_wells_spatial.csv`
    * `.../data/interim/new-mexico/nm_facilities.csv`
  * **Output Files:** * `.../data/interim/new-mexico/nm_wells_to_eog_sites.csv`
    * `.../data/interim/new-mexico/nm_facilities_to_eog_sites.csv`
* **Data Analysis Performed:**
  * **Geospatial Projection:** Converts basic latitude/longitude flat files into `GeoPandas` geometry points and standardizes all Coordinate Reference Systems to GPS `EPSG:4326`.
  * **Bounding Box Crop:** Clips the massive global EOG shapefile down to the Permian Basin bounding box prior to the join to optimize computational time.
  * **Point-in-Polygon Join:** Executes an inner spatial join (`predicate="within"`) to link discrete infrastructure points (API Numbers / Facility IDs) to the bounding polygons of EOG sites (`EOG_Site_ID`).

---

## 4. `download_multiyear_profiles.py`
**Purpose:** Targeted extraction of full historical flaring profiles (2012–Present) strictly for the sites mapped in the previous step.

* **Datasets Used:**
  * Infrastructure Crosswalks (from Step 3).
  * EOG VNF Multiyear Series Profiles (`site_{site_id}_multiyear_vnf_series.csv`).
* **Locations:**
  * **Sources:** `https://eogdata.mines.edu/wwwdata/downloads/vnf_profiles/profiles_multiyear/`
  * **Output File:** `~/work/projects/summer26-permian-flaring/data/raw/new-mexico/viirs/multiyear_catalog/permian_multiyear_profiles.csv`
* **Data Analysis Performed:**
  * **Dynamic Querying:** Aggregates unique `EOG_Site_ID`s from both the wells and facilities crosswalks to build a targeted fetch list.
  * **Column Pruning & Temporal Filtering:** Retains only crucial metrics (`temp_bb`, `rh`, `cloud_mask`), ensures data falls chronologically between 2012 and the present, and removes anomalous `999999` radiant heat readings on the fly. 

---

## 5. `build_site_timeseries.py`
**Purpose:** The central aggregation engine combining environmental remote-sensing data with local production and waste reporting.

* **Datasets Used:**
  * Historical Multiyear Profiles (`permian_multiyear_profiles.csv`).
  * New Mexico Reported Waste (`nm_upstream_waste_nonzero.csv`).
  * New Mexico Reported Oil Production (`nm_wcproduction_filtered.csv`).
  * Well and Facility Crosswalks.
* **Locations:**
  * **Sources:** Reads all inputs from the `data/interim/new-mexico/` and `data/raw/new-mexico/viirs/multiyear_catalog/` directories.
  * **Output Files:** * `.../data/interim/new-mexico/master_basin_timeseries_2012_2026.csv`
    * `.../data/interim/new-mexico/master_site_timeseries_2012_2026.csv`
* **Data Analysis Performed:**
  * **Macro-Aggregation (Basin-Wide):** Groups data by Year/Month. Sums total reported flared natural gas (MCF), total reported oil production (BBL), and total radiant heat (MW). Calculates a `Basin_VIIRS_Normalized_MW` metric by dividing total radiant heat by the count of clear (cloud-free) sensor observations.
  * **Micro-Aggregation (Site-Level):** Joins waste and production arrays onto the EOG Site boundaries using the crosswalk keys. Groups data by `EOG_Site_ID`, `Year`, and `Month` to produce granular, per-site time-series datasets detailing normalized radiant heat alongside explicitly reported waste and production yields. Outer joins ensure continuous timeline coverage even if a site lacks a report for a specific month.