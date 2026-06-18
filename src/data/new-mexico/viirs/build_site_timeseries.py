import pandas as pd
import os

# ==========================================
# 1. SETUP & SCHEMA CONFIGURATION
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
viirs_dir = os.path.join(project_root, 'data/raw/new-mexico/viirs/multiyear_catalog')

print("Loading datasets for time-series aggregation...")
df_waste = pd.read_csv(os.path.join(interim_dir, 'nm_upstream_waste_nonzero.csv'))
df_wells_cw = pd.read_csv(os.path.join(interim_dir, 'nm_wells_to_eog_sites.csv'))
df_fac_cw = pd.read_csv(os.path.join(interim_dir, 'nm_facilities_to_eog_sites.csv'))
df_viirs = pd.read_csv(os.path.join(viirs_dir, 'permian_multiyear_profiles.csv'))

# Load the exact production dataset
df_prod = pd.read_csv(os.path.join(interim_dir, 'nm_wcproduction_filtered.csv'))

# Standardize Keys to strings to prevent join failures
df_waste['Structure_ID'] = df_waste['Structure_ID'].astype(str).str.strip()
df_wells_cw['API_Number'] = df_wells_cw['API_Number'].astype(str).str.strip()
df_fac_cw['Facility_ID'] = df_fac_cw['Facility_ID'].astype(str).str.strip()
df_prod['API_Number'] = df_prod['API_Number'].astype(str).str.strip()

# ==========================================
# 2. MAP REGULATORY DATA TO EOG SITES
# ==========================================
print("Mapping state-reported waste and production to EOG Site boundaries...")

# --- Map Waste (Wells & Facilities) ---
df_waste_wells = pd.merge(df_waste, df_wells_cw[['API_Number', 'EOG_Site_ID']], left_on='Structure_ID', right_on='API_Number', how='inner')
df_waste_facs = pd.merge(df_waste, df_fac_cw[['Facility_ID', 'EOG_Site_ID']], left_on='Structure_ID', right_on='Facility_ID', how='inner')
df_waste_mapped = pd.concat([df_waste_wells, df_waste_facs])

# Filter waste for >= 2021 and aggregate monthly per site
df_waste_mapped = df_waste_mapped[df_waste_mapped['Year'] >= 2021]
df_site_waste = df_waste_mapped.groupby(['EOG_Site_ID', 'Year', 'Month'])['Volume_MCF'].sum().reset_index()
df_site_waste.rename(columns={'Volume_MCF': 'Reported_Flared_MCF'}, inplace=True)

# --- Map Production (Wells Only) ---
df_prod_mapped = pd.merge(df_prod, df_wells_cw[['API_Number', 'EOG_Site_ID']], on='API_Number', how='inner')
df_prod_mapped = df_prod_mapped[df_prod_mapped['Year'] >= 2021]

# Filter specifically for 'G' (Gas) to ensure we are comparing MCF to MCF
df_prod_gas = df_prod_mapped[df_prod_mapped['Product_Kind'] == 'G'].copy()

# Aggregate the explicit 'Volume' column
df_site_prod = df_prod_gas.groupby(['EOG_Site_ID', 'Year', 'Month'])['Volume'].sum().reset_index()
df_site_prod.rename(columns={'Volume': 'Reported_Produced_MCF'}, inplace=True)

# ==========================================
# 3. AGGREGATE VIIRS SATELLITE PROFILES
# ==========================================
print("Aggregating daily VIIRS profiles into monthly sums...")

date_col = 'Date_Mscan' if 'Date_Mscan' in df_viirs.columns else df_viirs.columns[0]
rh_col = 'RH' if 'RH' in df_viirs.columns else 'rh'

df_viirs['Date_Parsed'] = pd.to_datetime(df_viirs[date_col], errors='coerce')
df_viirs = df_viirs.dropna(subset=['Date_Parsed'])

df_viirs['Year'] = df_viirs['Date_Parsed'].dt.year
df_viirs['Month'] = df_viirs['Date_Parsed'].dt.month

df_viirs = df_viirs[df_viirs['Year'] >= 2021]

# Sum Radiant Heat (RH) for the month
df_site_viirs = df_viirs.groupby(['site_id', 'Year', 'Month'])[rh_col].sum().reset_index()
df_site_viirs.rename(columns={'site_id': 'EOG_Site_ID', rh_col: 'VIIRS_Radiant_Heat_Sum'}, inplace=True)

# ==========================================
# 4. MASTER MERGE & EXPORT
# ==========================================
print("Merging all data streams into master temporal dataset...")

# Use an outer merge so no timeline gaps occur if a site produces gas but reports zero flaring for a month
df_master = pd.merge(df_site_viirs, df_site_waste, on=['EOG_Site_ID', 'Year', 'Month'], how='outer')
df_master = pd.merge(df_master, df_site_prod, on=['EOG_Site_ID', 'Year', 'Month'], how='outer')

# Clean up NaN values (months with no reporting/detections become true zeros)
df_master.fillna(0, inplace=True)

# Create a clean datetime object for the Plotly x-axis
df_master['Date'] = pd.to_datetime(df_master[['Year', 'Month']].assign(DAY=1))
df_master = df_master.sort_values(by=['EOG_Site_ID', 'Date'])

output_path = os.path.join(interim_dir, 'master_site_timeseries_2021_2026.csv')
df_master.to_csv(output_path, index=False)
print(f"Success! Master Time-Series saved to: {output_path}")