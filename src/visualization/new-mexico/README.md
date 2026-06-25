# Permian Basin Flaring Analysis - Interactive Visualization Pipeline

This folder contains the data visualization pipeline for the Permian Flaring project. These Python scripts utilize `plotly` and `folium` to transform integrated spatial and temporal datasets into interactive HTML dashboards and satellite map overlays.

## Architecture Highlights
* **Temporal Auditing:** Interactive time-series charts contrasting satellite-detected radiant heat (VIIRS) directly against state-reported flaring and production volumes on shared timelines.
* **Spatial Auditing:** Geospatial maps overlaying exact coordinates of active infrastructure onto EOG's defined multi-year flaring footprints. It calculates volumetric containment rates by isolating emitters that report flaring but fall outside satellite detection zones.
* **Static Output:** All visualizers are compiled into standalone interactive HTML files requiring no backend server.

## Pipeline Scripts

### 1. `build_temporal_dashboards.py`
**Purpose:** Generates historical, high-level time-series profiles spanning the entire VIIRS catalogue (2012–2026).

* **Datasets Used:**
  * Macro Basin Timeseries (`master_basin_timeseries_2012_2026.csv`).
  * Micro Site Timeseries (`master_site_timeseries_2012_2026.csv`).
* **Source Location:** `~/work/projects/summer26-permian-flaring/data/interim/new-mexico/`
* **Data Analysis Performed:**
  * **Basin-Wide Macro Audit:** Plots normalized radiant heat (MW/Obs) against total reported flared volume (MCF) and reported oil production (BBL) for the entire basin.
  * **Site-Level Micro Audit:** Initializes an interactive Plotly dashboard featuring a dropdown menu. It dynamically recalculates visibility layers to plot the historical profile of whichever specific EOG Site ID the user selects.
* **Output Files:**
  * `visualizations/new-mexico/interactive_basin_aggregate.html`
  * `visualizations/new-mexico/interactive_site_widget.html`

### 2. `build_regulatory_dashboard.py`
**Purpose:** Focuses strictly on comparing reported state regulatory data: gas produced vs. gas flared.

* **Datasets Used:** Master Regulatory Timeseries (`master_regulatory_timeseries_2021_2026.csv`).
* **Source Location:** `~/work/projects/summer26-permian-flaring/data/interim/new-mexico/`
* **Data Analysis Performed:** Constructs an interactive Plotly widget tracking dual Y-axes for specific sites, isolating purely self-reported waste dynamics (Produced MCF vs. Flared Waste MCF) without the satellite heat variable.
* **Output File:** `visualizations/interactive_regulatory_widget.html`

### 3. `build_interactive_timeseries.py`
**Purpose:** An expanded version of the temporal audit dashboard, focusing on a more recent timeframe (2021-2026) and visualizing raw radiant heat rather than normalized heat.

* **Datasets Used:** Master Site Timeseries (`master_site_timeseries_2021_2026.csv`).
* **Source Location:** `~/work/projects/summer26-permian-flaring/data/interim/new-mexico/`
* **Data Analysis Performed:** Creates a unified interaction layer toggling between individual site IDs. It visualizes un-normalized VIIRS Radiant Heat (MW) on the primary axis against both State Reported Volumes (MCF Flared and MCF Produced) on a shared secondary axis.
* **Output File:** `visualizations/interactive_timeseries_widget.html`

### 4. `build_interactive_map_satellite.py`
**Purpose:** A foundational geospatial overlay mapping the physical reality of the wells against the EOG flaring polygons over an Esri World Imagery basemap.

* **Datasets Used:**
  * Master Wells Spatial Array (`nm_wells_spatial.csv`).
  * EOG Spatial Crosswalk (`nm_wells_to_eog_sites.csv`).
  * Native EOG Upstream Catalog (`upstream.shp`).
* **Source Locations:** * `data/interim/new-mexico/`
  * `data/raw/new-mexico/viirs/multiyear_catalog/VNF_multiyear_by_type_2012-2021_v20220822/`
* **Data Analysis Performed:**
  * **Status Filtering:** Purges inactive administrative 'ghost' records, isolating only physical wells with an 'Active' or 'New' status capable of flaring.
  * **Spatial Containment Mapping:** Merges well coordinates with the crosswalk file to categorize each well categorically as "Inside" or "Outside" a recognized EOG flare boundary.
  * **Visual Stacking:** Renders these filtered arrays over an interactive Folium satellite basemap, utilizing high-contrast neon geometries to differentiate containment status.
* **Output File:** `visualizations/interactive_permian_satellite_map.html`

### 5. `build_unified_audit_map.py`
**Purpose:** The capstone spatial analysis tool. It merges physical coordinates, spatial boundary containment, and reported non-zero flaring waste volumes into a single terminal audit.

* **Datasets Used:**
  * Spatial Arrays (`nm_wells_spatial.csv`, `nm_facilities.csv`).
  * EOG Spatial Crosswalks.
  * Native EOG Upstream Catalog (`upstream.shp`).
  * Reported Non-Zero Flaring Waste Ledger (`nm_upstream_waste_nonzero.csv`).
* **Source Locations:** `data/interim/new-mexico/` and `data/raw/new-mexico/viirs/...`
* **Data Analysis Performed:**
  * **Strict Non-Zero Emission Filtering:** Performs an inner join against the regulatory waste ledger, dropping any well or facility that *did not* report flaring waste between 2021-2026.
  * **Volumetric Weighting:** Scales the visual radius of the output markers dynamically on the map based on the severity of the reported volume (`radius_scale = Base + (Volume_MCF ** 0.15)`).
  * **Volumetric Capture Auditing:** Calculates aggregate arithmetic totals—computing exactly how many million cubic feet (MCF) of reported flaring occurred *inside* known satellite polygons versus how much leaked *outside* them.
* **Output:**
  * Visual: `visualizations/interactive_permian_audit_map.html`
  * Terminal Output: Generates a comprehensive string console report outlining "Basewide Volumetric Capture Rate" and "Basewide Volumetric Leakage Rate".