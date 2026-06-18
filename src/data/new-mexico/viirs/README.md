# VIIRS Satellite Ingestion & Processing Pipeline

This directory handles the raw extraction, in-memory cleaning, and temporal aggregation of Visible Infrared Imaging Radiometer Suite (VIIRS) Nightfire data collected by the Earth Observations Group (EOG).

## 📄 Contents
*   **`download_multiyear_profiles.py`**: A memory-less streaming script that queries EOG servers, processes data on-the-fly, and compiles 14 years of satellite observations.
*   **`build_site_timeseries.py`**: The master compilation engine that aligns daily satellite footprints with monthly state-reported oil production and waste metrics.

---

## 💡 Core Analytical Hypotheses
1. **The Physical Truth Metric**: Self-reported regulatory data is prone to reporting errors, administrative delays, or non-compliance. The absolute radiant heat (RH, measured in Megawatts) detected by satellite sensors serves as an immutable physical proxy for actual combustion volume.
2. **The Regime Change Shift (Pre vs. Post 2021)**: By pulling historical data back to 2012, we can evaluate the structural shift in operator behavior. We hypothesize a sharp divergence between oil production and observed flaring intensity following New Mexico's strict 2021 waste rules.
3. **The Flares-to-Barrels Ratio**: In a highly efficient field, radiant heat should track oil production linearly. Spikes in radiant heat without a corresponding increase in oil production indicate infrastructure bottlenecks (e.g., full gathering lines or compressor station outages).

---

## 🛠️ Code Logic & Architecture

### 1. True Memory-Less Streaming Ingestion
The extraction script (`download_multiyear_profiles.py`) avoids holding bulk rows in memory or thrashing the disk with temporary files. 
* **RAM-Only Slicing**: Raw text payloads are pulled from the `wwwdata` server directory via `requests` and transformed instantly into a string stream buffer using `io.StringIO`.
* **In-Flight Filtering**: Before being appended anywhere, the data is immediately stripped of 20+ unused instrument telemetry columns, filtered for `year >= 2012`, and checked for telemetry errors (`rh >= 999999`). 
* **Disk Append Logging**: Valid arrays are immediately flushed to the SSD using Pandas' append mode (`mode='a'`), and explicit Python garbage collection (`gc.collect()`) is triggered every 50 loops to permanently free up the RAM.

### 2. Multi-Resolution Time Alignment
The satellite captures nightly orbital snapshots, while state production records are logged as monthly blocks. `build_site_timeseries.py` loops through the daily data and uses group-by date math (`dt.year` and `dt.month`) to compile clean monthly totals mapped directly to individual EOG polygon IDs.