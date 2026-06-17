import pandas as pd
import geopandas as gpd
import os

# ==========================================
# 1. SETUP & PATHS
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
catalog_dir = os.path.join(project_root, 'data/raw/new-mexico/viirs/multiyear_catalog/VNF_multiyear_by_type_2012-2021_v20220822')

print("Loading Infrastructure Datasets...")
df_wells = pd.read_csv(os.path.join(interim_dir, 'nm_wells_spatial.csv'))
df_facilities = pd.read_csv(os.path.join(interim_dir, 'nm_facilities.csv'))

# ==========================================
# 2. LOAD & FILTER NATIVE SHAPEFILE
# ==========================================
shp_path = os.path.join(catalog_dir, 'upstream.shp')
print(f"Loading native Shapefile from: {shp_path}")

# GeoPandas reads the binary shapefile natively
gdf_catalog = gpd.read_file(shp_path)

# Normalize column names to lowercase
gdf_catalog.columns = [str(c).strip().lower() for c in gdf_catalog.columns]

# Print the available columns so you can physically see the DBF structure
print(f"Available Shapefile columns: {gdf_catalog.columns.tolist()}")

# --> THE FIX: Explicitly target the 'index' column instead of guessing
id_col = 'index'

# A quick safety check in case the Shapefile DBF renamed 'index' slightly
if id_col not in gdf_catalog.columns:
    print(f"\n[!] CRITICAL WARNING: '{id_col}' not found in the Shapefile!")
    print("Please look at the column list printed above and update the id_col variable.")

# Ensure the coordinate reference system (CRS) is standard GPS (EPSG:4326)
if gdf_catalog.crs is None or gdf_catalog.crs.to_epsg() != 4326:
    gdf_catalog = gdf_catalog.to_crs(epsg=4326)

# Filter the massive global catalog down to just the Permian Bounding Box
LAT_MIN, LAT_MAX = 31.9, 33.6
LON_MIN, LON_MAX = -105.0, -102.9

gdf_catalog_permian = gdf_catalog.cx[LON_MIN:LON_MAX, LAT_MIN:LAT_MAX].copy()
print(f"Filtered to {len(gdf_catalog_permian)} catalog sites within the Permian Basin.")

# ==========================================
# 3. BUILD INFRASTRUCTURE GEODATAFRAMES
# ==========================================
print("Building Point Geometries for Wells and Facilities...")

# Convert Wells (using exact capitalization from your files)
gdf_wells = gpd.GeoDataFrame(
    df_wells, 
    geometry=gpd.points_from_xy(df_wells['Longitude'], df_wells['Latitude']), 
    crs="EPSG:4326"
)

# Convert Facilities (using exact lowercase from your files)
gdf_facilities = gpd.GeoDataFrame(
    df_facilities, 
    geometry=gpd.points_from_xy(df_facilities['longitude'], df_facilities['latitude']), 
    crs="EPSG:4326"
)

# ==========================================
# 4. PERFORM THE SPATIAL JOIN (POINT-IN-POLYGON)
# ==========================================
print("Executing Spatial Intersection...")

# Match Wells to Sites
matched_wells = gpd.sjoin(gdf_wells, gdf_catalog_permian, how="inner", predicate="within")

# Match Facilities to Sites
matched_facilities = gpd.sjoin(gdf_facilities, gdf_catalog_permian, how="inner", predicate="within")

print(f"Results: Successfully matched {len(matched_wells)} Wells and {len(matched_facilities)} Facilities to EOG Polygons.")

# ==========================================
# 5. CLEAN UP AND EXPORT CROSSWALKS
# ==========================================
print("Exporting Crosswalks...")

# --- WELLS CROSSWALK ---
# Detect if the EOG ID was renamed to 'id_right' due to a column clash
eog_id_wells = id_col + '_right' if id_col + '_right' in matched_wells.columns else id_col

# Dynamically keep only columns that actually exist to prevent KeyErrors
cols_to_keep_wells = ['API_Number', 'Latitude', 'Longitude', eog_id_wells]
cols_to_keep_wells = [c for c in cols_to_keep_wells if c in matched_wells.columns]

df_wells_crosswalk = matched_wells[cols_to_keep_wells].rename(columns={eog_id_wells: 'EOG_Site_ID'})

# --- FACILITIES CROSSWALK ---
# Apply the same clash-detection logic for facilities
eog_id_fac = id_col + '_right' if id_col + '_right' in matched_facilities.columns else id_col
fac_id_col = 'id_left' if 'id_left' in matched_facilities.columns else 'id'

# Ensure we grab the facility name and coordinates safely
cols_to_keep_fac = [fac_id_col, 'name', 'latitude', 'longitude', eog_id_fac]
cols_to_keep_fac = [c for c in cols_to_keep_fac if c in matched_facilities.columns]

df_facilities_crosswalk = matched_facilities[cols_to_keep_fac].rename(
    columns={eog_id_fac: 'EOG_Site_ID', fac_id_col: 'Facility_ID'}
)

# --- EXPORT ---
output_wells = os.path.join(interim_dir, 'nm_wells_to_eog_sites.csv')
output_facilities = os.path.join(interim_dir, 'nm_facilities_to_eog_sites.csv')

df_wells_crosswalk.to_csv(output_wells, index=False)
df_facilities_crosswalk.to_csv(output_facilities, index=False)

print("\n" + "-" * 60)
print(f"Crosswalks Generated:")
print(f"1. {output_wells}")
print(f"2. {output_facilities}")