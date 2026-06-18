import pandas as pd
import geopandas as gpd
import folium
import os

# ==========================================
# 1. SETUP & PATH CONFIGURATION
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
catalog_dir = os.path.join(project_root, 'data/raw/new-mexico/viirs/multiyear_catalog/VNF_multiyear_by_type_2012-2021_v20220822')
viz_dir = os.path.join(project_root, 'visualizations')

os.makedirs(viz_dir, exist_ok=True)

print("Loading Infrastructure Datasets and Regulatory Ledgers...")
df_all_wells = pd.read_csv(os.path.join(interim_dir, 'nm_wells_spatial.csv'))
df_facilities = pd.read_csv(os.path.join(interim_dir, 'nm_facilities.csv'))

df_wells_crosswalk = pd.read_csv(os.path.join(interim_dir, 'nm_wells_to_eog_sites.csv'))
df_fac_crosswalk = pd.read_csv(os.path.join(interim_dir, 'nm_facilities_to_eog_sites.csv'))
df_waste = pd.read_csv(os.path.join(interim_dir, 'nm_upstream_waste_nonzero.csv'))

# Load the native EOG Shapefile
gdf_catalog = gpd.read_file(os.path.join(catalog_dir, 'upstream.shp'))
gdf_catalog.columns = [str(c).strip().lower() for c in gdf_catalog.columns]

# ==========================================
# 2. KEY STANDARDIZATION & STATUS FILTERING
# ==========================================
print("Standardizing relational cross-reference keys...")

# Enforce clean string casting to prevent numeric vs string join failures
df_waste['Structure_ID'] = df_waste['Structure_ID'].astype(str).str.strip()
df_all_wells['API_Number'] = df_all_wells['API_Number'].astype(str).str.strip()
df_wells_crosswalk['API_Number'] = df_wells_crosswalk['API_Number'].astype(str).str.strip()

df_facilities['id'] = df_facilities['id'].astype(str).str.strip()
df_fac_crosswalk['Facility_ID'] = df_fac_crosswalk['Facility_ID'].astype(str).str.strip()

# Retain only physically valid operating statuses
df_all_wells = df_all_wells[df_all_wells['Well_Status'].isin(['Active', 'New'])].copy()

# ==========================================
# 3. AGGREGATE REGULATORY FLARING (2021 - 2026)
# ==========================================
print("Aggregating 2021-2026 non-zero waste volumes...")
df_waste_filtered = df_waste[(df_waste['Year'] >= 2021) & (df_waste['Year'] <= 2026)].copy()
df_waste_agg = df_waste_filtered.groupby('Structure_ID')['Volume_MCF'].sum().reset_index()

# ==========================================
# 4. AUDIT WELLS LAYER (STRICT NON-ZERO FILTER)
# ==========================================
print("Filtering for active/new wells with reported volumes...")
# Using an inner join drops any well not present in the non-zero waste ledger
df_wells_audit = pd.merge(df_all_wells, df_waste_agg, left_on='API_Number', right_on='Structure_ID', how='inner')

# Map containment vectors using the spatial crosswalk
df_wells_audit = pd.merge(df_wells_audit, df_wells_crosswalk[['API_Number', 'EOG_Site_ID']], on='API_Number', how='left')

df_wells_inside = df_wells_audit[df_wells_audit['EOG_Site_ID'].notna()].copy()
df_wells_outside = df_wells_audit[df_wells_audit['EOG_Site_ID'].isna()].copy()

# ==========================================
# 5. AUDIT FACILITIES LAYER (STRICT NON-ZERO FILTER)
# ==========================================
print("Filtering for midstream facilities with reported volumes...")
# Using an inner join drops any facility not present in the non-zero waste ledger
df_fac_audit = pd.merge(df_facilities, df_waste_agg, left_on='id', right_on='Structure_ID', how='inner')

# Map containment vectors using the spatial crosswalk
df_fac_audit = pd.merge(df_fac_audit, df_fac_crosswalk[['Facility_ID', 'EOG_Site_ID']], left_on='id', right_on='Facility_ID', how='left')

df_fac_inside = df_fac_audit[df_fac_audit['EOG_Site_ID'].notna()].copy()
df_fac_outside = df_fac_audit[df_fac_audit['EOG_Site_ID'].isna()].copy()

# ==========================================
# 6. INTEGRATE AUDIT METRICS SUMMARY
# ==========================================
wells_vol_inside = df_wells_inside['Volume_MCF'].sum()
wells_vol_outside = df_wells_outside['Volume_MCF'].sum()

fac_vol_inside = df_fac_inside['Volume_MCF'].sum()
fac_vol_outside = df_fac_outside['Volume_MCF'].sum()

total_vol_inside = wells_vol_inside + fac_vol_inside
total_vol_outside = wells_vol_outside + fac_vol_outside
grand_total_reported = total_vol_inside + total_vol_outside

# ==========================================
# 7. FILTER GEOMETRIC OVERLAYS
# ==========================================
print("Isolating corresponding EOG polygons...")
active_site_ids = pd.concat([df_wells_inside['EOG_Site_ID'], df_fac_inside['EOG_Site_ID']]).unique()
gdf_matched_polygons = gdf_catalog[gdf_catalog['index'].isin(active_site_ids)].copy()

if gdf_matched_polygons.crs is None or gdf_matched_polygons.crs.to_epsg() != 4326:
    gdf_matched_polygons = gdf_matched_polygons.to_crs(epsg=4326)

# ==========================================
# 8. CONSTRUCT INTERACTIVE SATELLITE VISUALIZATION
# ==========================================
print("Assembling interactive web map layers...")
esri_satellite_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
esri_attribution = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'

m = folium.Map(location=[32.5, -103.5], zoom_start=9, tiles=esri_satellite_url, attr=esri_attribution)
folium.TileLayer('CartoDB positron', name='Minimalist Light Map').add_to(m)

# --- LAYER 1: Flare Footprints (Neon Yellow Polygons) ---
folium.GeoJson(
    gdf_matched_polygons,
    name="EOG Flare Boundaries",
    style_function=lambda feature: {
        'fillColor': '#ffff00', 'color': '#ffff00', 'weight': 1.5, 'fillOpacity': 0.12
    },
    tooltip=folium.GeoJsonTooltip(fields=['index'], aliases=['EOG Site ID:'])
).add_to(m)

# --- LAYER 2: Contained Emitters (Neon Colors) ---
group_inside = folium.FeatureGroup(name="Reporting Assets Inside Polygons")

# Inside Wells (Neon Cyan Circles)
for idx, row in df_wells_inside.iterrows():
    radius_scale = 3.0 + (row['Volume_MCF'] ** 0.15)
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']], radius=min(radius_scale, 14),
        color='#00f0ff', fill=True, fill_color='#00f0ff', fill_opacity=0.85,
        tooltip=f"<b>WELL (Inside)</b><br><b>API:</b> {row['API_Number']}<br><b>Reported Volume:</b> {row['Volume_MCF']:,.1f} MCF"
    ).add_to(group_inside)

# Inside Facilities (Neon Green Circles)
for idx, row in df_fac_inside.iterrows():
    radius_scale = 4.5 + (row['Volume_MCF'] ** 0.15)
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']], radius=min(radius_scale, 16),
        color='#00ff66', fill=True, fill_color='#00ff66', fill_opacity=0.9,
        tooltip=f"<b>MIDSTREAM FACILITY (Inside)</b><br><b>Name:</b> {row['name']}<br><b>ID:</b> {row['id']}<br><b>Reported Volume:</b> {row['Volume_MCF']:,.1f} MCF"
    ).add_to(group_inside)

group_inside.add_to(m)

# --- LAYER 3: Uncontained Emitters (Stark White/Grey) ---
group_outside = folium.FeatureGroup(name="Reporting Assets Outside Polygons")

# Outside Wells (White Circles)
for idx, row in df_wells_outside.iterrows():
    radius_scale = 2.5 + (row['Volume_MCF'] ** 0.15)
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']], radius=min(radius_scale, 14),
        color='#ffffff', fill=True, fill_color='#ffffff', fill_opacity=0.7,
        tooltip=f"<b>WELL (Outside)</b><br><b>API:</b> {row['API_Number']}<br><b>Reported Volume:</b> {row['Volume_MCF']:,.1f} MCF"
    ).add_to(group_outside)

# Outside Facilities (Light Grey Circles)
for idx, row in df_fac_outside.iterrows():
    radius_scale = 4.0 + (row['Volume_MCF'] ** 0.15)
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']], radius=min(radius_scale, 16),
        color='#e5e5e5', fill=True, fill_color='#b5b5b5', fill_opacity=0.75,
        tooltip=f"<b>MIDSTREAM FACILITY (Outside)</b><br><b>Name:</b> {row['name']}<br><b>ID:</b> {row['id']}<br><b>Reported Volume:</b> {row['Volume_MCF']:,.1f} MCF"
    ).add_to(group_outside)

group_outside.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# Save visualization HTML
output_html = os.path.join(viz_dir, 'interactive_permian_audit_map.html')
m.save(output_html)

# ==========================================
# 9. COMPREHENSIVE TERMINAL AUDIT SUMMARY
# ==========================================
print("\n" + "="*60)
print("     PERMIAN NON-ZERO EMITTER SPATIAL AUDIT METRICS")
print("============================================================")
print(f"Total Non-Zero Reporting Wells Tracked     : {len(df_wells_audit):,}")
print(f"Total Non-Zero Reporting Facilities Tracked: {len(df_fac_audit):,}")
print("-"*60)
print(f"Reporting Wells Inside Polygons            : {len(df_wells_inside):,}")
print(f"Reporting Wells Outside Polygons           : {len(df_wells_outside):,}")
print(f"Reporting Facilities Inside Polygons       : {len(df_fac_inside):,}")
print(f"Reporting Facilities Outside Polygons      : {len(df_fac_outside):,}")
print("-"*60)
print(f"Reported Well Flaring INSIDE               : {wells_vol_inside:,.2f} MCF")
print(f"Reported Well Flaring OUTSIDE              : {wells_vol_outside:,.2f} MCF")
print(f"Reported Facility Flaring INSIDE           : {fac_vol_inside:,.2f} MCF")
print(f"Reported Facility Flaring OUTSIDE          : {fac_vol_outside:,.2f} MCF")
print("="*60)
print(f"TOTAL REPORTED VOLUME INSIDE POLYGONS      : {total_vol_inside:,.2f} MCF")
print(f"TOTAL REPORTED VOLUME OUTSIDE POLYGONS     : {total_vol_outside:,.2f} MCF")
print("-"*60)

if grand_total_reported > 0:
    pct_inside = (total_vol_inside / grand_total_reported) * 100
    pct_outside = (total_vol_outside / grand_total_reported) * 100
    print(f"Basewide Volumetric Capture Rate           : {pct_inside:.2f}%")
    print(f"Basewide Volumetric Leakage Rate           : {pct_outside:.2f}%")
print("============================================================")
print(f"Interactive Audit Map Successfully Generated at:\n{output_html}")
print("============================================================")