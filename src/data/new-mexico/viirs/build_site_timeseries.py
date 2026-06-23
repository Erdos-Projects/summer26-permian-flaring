import pandas as pd
import numpy as np
import os

# ==========================================
# 1. SETUP & SCHEMA CONFIGURATION
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
viirs_dir = os.path.join(project_root, 'data/raw/new-mexico/viirs/multiyear_catalog')

print("Loading historical datasets for aggregation...")
df_waste = pd.read_csv(os.path.join(interim_dir, 'nm_upstream_waste_nonzero.csv'))
df_prod = pd.read_csv(os.path.join(interim_dir, 'nm_wcproduction_filtered.csv'))
df_viirs = pd.read_csv(os.path.join(viirs_dir, 'permian_multiyear_profiles.csv'))

df_wells_cw = pd.read_csv(os.path.join(interim_dir, 'nm_wells_to_eog_sites.csv'))
df_fac_cw = pd.read_csv(os.path.join(interim_dir, 'nm_facilities_to_eog_sites.csv'))

df_waste['Structure_ID'] = df_waste['Structure_ID'].astype(str).str.strip()
df_wells_cw['API_Number'] = df_wells_cw['API_Number'].astype(str).str.strip()
df_fac_cw['Facility_ID'] = df_fac_cw['Facility_ID'].astype(str).str.strip()
df_prod['API_Number'] = df_prod['API_Number'].astype(str).str.strip()

df_viirs['date_mscan'] = pd.to_datetime(df_viirs['date_mscan'], errors='coerce')
df_viirs = df_viirs.dropna(subset=['date_mscan'])
df_viirs['Year'] = df_viirs['date_mscan'].dt.year
df_viirs['Month'] = df_viirs['date_mscan'].dt.month

df_prod = df_prod[df_prod['Year'] >= 2012]
df_viirs = df_viirs[df_viirs['Year'] >= 2012]
df_prod_oil = df_prod[df_prod['Product_Kind'] == 'O'].copy()

# Create a master clear-sky dataframe to use for all downstream calculations
df_viirs_clear = df_viirs[df_viirs['cloud_mask'] == 0].copy()

# ==========================================
# 2. MACRO: BASIN-WIDE AGGREGATION
# ==========================================
print("Aggregating historical macro-level metrics...")
df_basin_waste = df_waste.groupby(['Year', 'Month'])['Volume_MCF'].sum().reset_index()
df_basin_waste.rename(columns={'Volume_MCF': 'Basin_Reported_Flared_MCF'}, inplace=True)

df_basin_oil = df_prod_oil.groupby(['Year', 'Month'])['Volume'].sum().reset_index()
df_basin_oil.rename(columns={'Volume': 'Basin_Reported_Oil_BBL'}, inplace=True)

# Calculate sum of all radiant heat (ONLY for clear observations)
df_basin_viirs_sum = df_viirs_clear.groupby(['Year', 'Month'])['rh'].sum().reset_index()
df_basin_viirs_sum.rename(columns={'rh': 'Basin_VIIRS_Heat_MW_Sum'}, inplace=True)

# Count clear observations
df_basin_clear = df_viirs_clear.groupby(['Year', 'Month']).size().reset_index(name='Basin_Clear_Obs')

df_basin_master = pd.merge(df_basin_viirs_sum, df_basin_clear, on=['Year', 'Month'], how='left')
df_basin_master['Basin_Clear_Obs'] = df_basin_master['Basin_Clear_Obs'].fillna(0)

# Calculate Normalized RH (Safely catching division by zero)
df_basin_master['Basin_VIIRS_Normalized_MW'] = (df_basin_master['Basin_VIIRS_Heat_MW_Sum'] / df_basin_master['Basin_Clear_Obs']).replace([np.inf, -np.inf], 0).fillna(0)

df_basin_master = pd.merge(df_basin_master, df_basin_oil, on=['Year', 'Month'], how='outer')
df_basin_master = pd.merge(df_basin_master, df_basin_waste, on=['Year', 'Month'], how='outer').fillna(0)
df_basin_master['Date'] = pd.to_datetime(df_basin_master[['Year', 'Month']].assign(DAY=1))
df_basin_master = df_basin_master.sort_values('Date')

basin_output = os.path.join(interim_dir, 'master_basin_timeseries_2012_2026.csv')
df_basin_master.to_csv(basin_output, index=False)

# ==========================================
# 3. MICRO: SITE-LEVEL AGGREGATION
# ==========================================
print("Mapping historical data to EOG Site boundaries...")
df_waste_wells = pd.merge(df_waste, df_wells_cw[['API_Number', 'EOG_Site_ID']], left_on='Structure_ID', right_on='API_Number', how='inner')
df_waste_facs = pd.merge(df_waste, df_fac_cw[['Facility_ID', 'EOG_Site_ID']], left_on='Structure_ID', right_on='Facility_ID', how='inner')
df_site_waste = pd.concat([df_waste_wells, df_waste_facs]).groupby(['EOG_Site_ID', 'Year', 'Month'])['Volume_MCF'].sum().reset_index()
df_site_waste.rename(columns={'Volume_MCF': 'Reported_Flared_MCF'}, inplace=True)

df_prod_oil_mapped = pd.merge(df_prod_oil, df_wells_cw[['API_Number', 'EOG_Site_ID']], on='API_Number', how='inner')
df_site_oil = df_prod_oil_mapped.groupby(['EOG_Site_ID', 'Year', 'Month'])['Volume'].sum().reset_index()
df_site_oil.rename(columns={'Volume': 'Reported_Oil_Produced_BBL'}, inplace=True)

# Calculate sum of site radiant heat (ONLY for clear observations)
df_site_viirs_sum = df_viirs_clear.groupby(['site_id', 'Year', 'Month'])['rh'].sum().reset_index()
df_site_viirs_sum.rename(columns={'rh': 'Site_VIIRS_Heat_MW_Sum'}, inplace=True)

# Count site clear observations
df_site_clear = df_viirs_clear.groupby(['site_id', 'Year', 'Month']).size().reset_index(name='Site_Clear_Obs')

df_site_viirs = pd.merge(df_site_viirs_sum, df_site_clear, on=['site_id', 'Year', 'Month'], how='left')
df_site_viirs['Site_Clear_Obs'] = df_site_viirs['Site_Clear_Obs'].fillna(0)

# Calculate Normalized RH (Safely catching division by zero)
df_site_viirs['VIIRS_Normalized_MW'] = (df_site_viirs['Site_VIIRS_Heat_MW_Sum'] / df_site_viirs['Site_Clear_Obs']).replace([np.inf, -np.inf], 0).fillna(0)
df_site_viirs.rename(columns={'site_id': 'EOG_Site_ID'}, inplace=True)

df_site_master = pd.merge(df_site_viirs, df_site_oil, on=['EOG_Site_ID', 'Year', 'Month'], how='outer')
df_site_master = pd.merge(df_site_master, df_site_waste, on=['EOG_Site_ID', 'Year', 'Month'], how='outer').fillna(0)
df_site_master['Date'] = pd.to_datetime(df_site_master[['Year', 'Month']].assign(DAY=1))
df_site_master = df_site_master.sort_values(by=['EOG_Site_ID', 'Date'])

site_output = os.path.join(interim_dir, 'master_site_timeseries_2012_2026.csv')
df_site_master.to_csv(site_output, index=False)