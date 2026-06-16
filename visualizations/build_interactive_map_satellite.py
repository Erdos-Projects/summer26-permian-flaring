import pandas as pd
import geopandas as gpd
import folium
import os

# ==========================================
# 1. SETUP & PATHS
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
catalog_dir = os.path.join(project_root, 'data/raw/new-mexico/viirs/multiyear_catalog/VNF_multiyear_by_type_2012-2021_v20220822')
viz_dir = os.path.join(project_root, 'visualizations')

os.makedirs(viz_dir, exist_ok=True)

print("Loading Master Spatial Data and Crosswalks...")
df_all_wells = pd.read_csv(os.path.join(interim_dir, 'nm_wells_spatial.csv'))

# --- NEW FILTER LOGIC ---
print("Filtering out administrative 'ghost' wells...")
# Keep only wells that physically exist and are capable of flaring
target_statuses = ['Active', 'New']
df_all_wells = df_all_wells[df_all_wells['Well_Status'].isin(target_statuses)].copy()
# ------------------------

df_crosswalk = pd.read_csv(os.path.join(interim_dir, 'nm_wells_to_eog_sites.csv'))

# Load the native EOG Shapefile
gdf_catalog = gpd.read_file(os.path.join(catalog_dir, 'upstream.shp'))
gdf_catalog.columns = [str(c).strip().lower() for c in gdf_catalog.columns]

# ==========================================
# 2. SEPARATE INSIDE VS. OUTSIDE WELLS
# ==========================================
print("Categorizing wells by polygon containment status...")
df_merged_wells = pd.merge(
    df_all_wells, 
    df_crosswalk[['API_Number', 'EOG_Site_ID']], 
    on='API_Number', 
    how='left'
)

df_wells_inside = df_merged_wells[df_merged_wells['EOG_Site_ID'].notna()].copy()
df_wells_outside = df_merged_wells[df_merged_wells['EOG_Site_ID'].isna()].copy()

# ==========================================
# 3. FILTER & ALIGN SHAPEFILE POLYGONS
# ==========================================
print("Filtering EOG shapefile polygons...")
matched_site_ids = df_wells_inside['EOG_Site_ID'].unique()
gdf_matched_polygons = gdf_catalog[gdf_catalog['index'].isin(matched_site_ids)].copy()

if gdf_matched_polygons.crs is None or gdf_matched_polygons.crs.to_epsg() != 4326:
    gdf_matched_polygons = gdf_matched_polygons.to_crs(epsg=4326)

# ==========================================
# 4. INITIALIZE MAP WITH SATELLITE BASEMAP
# ==========================================
print("Constructing interactive folium map layer stack...")

# Define the Esri World Imagery URL endpoint
esri_satellite_url = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
esri_attribution = 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'

# Initialize map with the satellite layer as the default basemap option
m = folium.Map(
    location=[32.5, -103.5], 
    zoom_start=9, 
    tiles=esri_satellite_url, 
    attr=esri_attribution,
    name='Esri Satellite'
)

# Add a secondary light basemap option into the system architecture for flexibility
folium.TileLayer('CartoDB positron', name='Minimalist Light Map').add_to(m)

# --- LAYER 1: EOG Polygons (High-Contrast Neon Yellow) ---
folium.GeoJson(
    gdf_matched_polygons,
    name="EOG Flare Boundaries",
    style_function=lambda feature: {
        'fillColor': '#ffff00',  # Electric neon yellow pops over dark/tan ground textures
        'color': '#ffff00',
        'weight': 2,             # Slightly heavier border thickness to preserve definition
        'fillOpacity': 0.15      # Low opacity preserves underlying view of the actual well pads
    },
    tooltip=folium.GeoJsonTooltip(fields=['index'], aliases=['EOG Site ID:'])
).add_to(m)

# --- LAYER 2: Contained Wells (Electric Neon Cyan) ---
group_inside = folium.FeatureGroup(name="Wells Inside Polygons")
for idx, row in df_wells_inside.iterrows():
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=2.5,
        color='#00f0ff',        # High-intensity electric cyan cuts through dark backgrounds cleanly
        fill=True,
        fill_color='#00f0ff',
        fill_opacity=0.9,
        tooltip=f"<b>API:</b> {row['API_Number']}<br><b>Status:</b> Inside Polygon<br><b>EOG Site:</b> {int(row['EOG_Site_ID'])}"
    ).add_to(group_inside)
group_inside.add_to(m)

# --- LAYER 3: Uncontained Wells (Stark Stark White) ---
group_outside = folium.FeatureGroup(name="Wells Outside Polygons (No Flare Detections)")
for idx, row in df_wells_outside.iterrows():
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=2.0,
        color='#ffffff',        # Pure white markers break through desert or vegetation noise patterns
        fill=True,
        fill_color='#ffffff',
        fill_opacity=0.6,       # Scaled down opacity to prevent background crowding
        tooltip=f"<b>API:</b> {row['API_Number']}<br><b>Status:</b> Outside Polygon"
    ).add_to(group_outside)
group_outside.add_to(m)

# --- LAYER CONTROLS ---
folium.LayerControl(collapsed=False).add_to(m)

# ==========================================
# 5. EXPORT AND OUTPUT
# ==========================================
output_html = os.path.join(viz_dir, 'interactive_permian_satellite_map.html')
m.save(output_html)

print("\n" + "-" * 60)
print("Satellite Visualizer Map Successfully Generated!")
print(f"Total 'Active/New' Wells Inside Polygons: {len(df_wells_inside)}")
print(f"Total 'Active/New' Wells Outside Polygons: {len(df_wells_outside)}")
print(f"Launch the webpage in your browser to inspect the terrain overlay: {output_html}")