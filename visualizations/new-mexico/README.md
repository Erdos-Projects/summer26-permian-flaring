# Spatial & Temporal Visualization Dashboards

This subfolder houses the rendering engine that transforms our aggregated historical datasets into interactive, browser-ready geographic and temporal dashboards.

## 📄 Contents
*   **`build_unified_audit_map.py`**: Merges asset locations with regulatory ledgers and outputs a geographic audit map superimposed on satellite imagery.
*   **`build_temporal_dashboards.py`**: Generates high-performance, dark-mode, multi-axis interactive charts showing long-term historical performance profiles.

---

## 💡 Core Analytical Hypotheses
1. **Solving the Data Pancake Effect**: Oil production metrics (millions of barrels) completely dwarf regulatory flaring metrics (thousands of MCF). Plotting them on a single axis renders the flaring metrics unreadable. A triple-axis presentation layout exposes structural trends across variables regardless of scale differences.
2. **Spatial Leakage vs. Spatial Capture**: Assets reporting volumes to the state should display a clear spatial overlap with infrared satellite heat footprints. Emitters reporting waste *outside* known infrared polygons represent unverified leakage points or unmapped flaring.

---

## 🛠️ Code Logic & Architecture

### 1. Geographic Rendering Engine (Folium)
* **Logarithmic Metric Scaling**: Circle marker radii are dynamically calculated on-the-fly using power functions (`3.0 + Volume ** 0.15`). This compresses severe outliers and ensures massive super-emitters do not visually cover entire counties while keeping tiny emitters visible.
* **Categorical Styling**: Uses high-contrast neon styling against an ESRI World Imagery satellite base layer to group data at a glance:
  * 🔵 **Neon Cyan (`#00f0ff`)**: Well Pad inside an active thermal footprint.
  * 🟢 **Neon Green (`#00ff66`)**: Midstream Facility inside an active thermal footprint.
  * ⚪ **Stark White / Grey**: Outlier emitters operating outside known infrared zones.

### 2. Triple-Axis Layout Engineering (Plotly)
To plot three completely distinct measurement units (Radiant Heat in MW, Flared Volume in MCF, and Oil Production in BBL) seamlessly on a single plot canvas, the pipeline re-engineers Plotly's standard rendering layout:
* **Domain Compression**: The main chart width is compressed to `85%` of the page width (`domain=[0.0, 0.85]`).
* **Axis Stacking**: The remaining `15%` of horizontal screen space is utilized to create an isolated, floating third vertical axis anchored at `position=0.95`. This keeps all lines fully maximized and perfectly readable across the page.