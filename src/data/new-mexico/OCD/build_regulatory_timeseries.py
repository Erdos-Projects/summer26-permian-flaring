import pandas as pd
import os

# ==========================================
# 1. SETUP & SCHEMA CONFIGURATION
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')

print("Loading state regulatory datasets...")
df_waste = pd.read_csv(os.path.join(interim_dir, 'nm_upstream_waste_nonzero.csv'))
df_wells_cw = pd.read_csv(os.path.join(interim_dir, 'nm_wells_to_eog_sites.csv'))
df_fac_cw = pd.read_csv(os.path.join(interim_dir, 'nm_facilities_to_eog_sites.csv'))
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

# Filter for post-2021 and specifically for 'G' (Gas) to ensure MCF-to-MCF comparison
df_prod_mapped = df_prod_mapped[(df_prod_mapped['Year'] >= 2021) & (df_prod_mapped['Product_Kind'] == 'G')]

# Aggregate the explicit 'Volume' column
df_site_prod = df_prod_mapped.groupby(['EOG_Site_ID', 'Year', 'Month'])['Volume'].sum().reset_index()
df_site_prod.rename(columns={'Volume': 'Reported_Produced_MCF'}, inplace=True)

# ==========================================
# 3. MASTER MERGE & EXPORT
# ==========================================
print("Merging data streams into master temporal dataset...")

# Use an outer merge to preserve timelines if a site produces gas but reports zero flaring for a month
df_master = pd.merge(df_site_waste, df_site_prod, on=['EOG_Site_ID', 'Year', 'Month'], how='outer')

# Clean up NaN values (months with no reporting become true zeros)
df_master.fillna(0, inplace=True)

# Create a clean datetime object for the Plotly x-axis
df_master['Date'] = pd.to_datetime(df_master[['Year', 'Month']].assign(DAY=1))
df_master = df_master.sort_values(by=['EOG_Site_ID', 'Date'])

output_path = os.path.join(interim_dir, 'master_regulatory_timeseries_2021_2026.csv')
df_master.to_csv(output_path, index=False)
print(f"Success! Master Time-Series saved to: {output_path}")