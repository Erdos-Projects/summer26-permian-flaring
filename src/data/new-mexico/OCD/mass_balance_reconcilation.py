import pandas as pd
import numpy as np
import os

# ==========================================
# 1. SETUP PATHS & LOAD DATA
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')

# Input paths for the four newly flattened datasets
prod_path = os.path.join(project_root, 'data/interim/new-mexico/nm_wcproduction_filtered.csv')
sales_path = os.path.join(project_root, 'data/interim/new-mexico/nm_gas_sold.csv')
waste_path = os.path.join(project_root, 'data/interim/new-mexico/nm_upstream_waste_nonzero.csv')
ben_use_path = os.path.join(project_root, 'data/interim/new-mexico/nm_upstream_beneficial_use_nonzero.csv')

print("Loading datasets into Pandas...")
df_prod = pd.read_csv(prod_path)
df_sales = pd.read_csv(sales_path)
df_waste = pd.read_csv(waste_path)
df_ben_use = pd.read_csv(ben_use_path)


# ==========================================
# 2. STANDARDIZE COLUMN NAMES & TYPES
# ==========================================
print("Standardizing types and filtering for Gas...")

# --- PRODUCTION ---
# Only reconcile Gas ('G')
df_prod = df_prod[df_prod['Product_Kind'] == 'G'].copy()
df_prod['Year'] = pd.to_numeric(df_prod['Year'], errors='coerce')
df_prod['Month'] = pd.to_numeric(df_prod['Month'], errors='coerce')
df_prod['Operator_ID'] = pd.to_numeric(df_prod['Operator_ID'], errors='coerce')
df_prod['gas_vol'] = pd.to_numeric(df_prod['Volume'], errors='coerce').fillna(0)

# --- SALES ---
# No more Well_Count division! Pure volume.
df_sales['Year'] = pd.to_numeric(df_sales['Year'], errors='coerce')
df_sales['Month'] = pd.to_numeric(df_sales['Month'], errors='coerce')
df_sales['Operator_ID'] = pd.to_numeric(df_sales['Operator_ID'], errors='coerce')
df_sales['Gas_Sold_MCF'] = pd.to_numeric(df_sales['Gas_Sold_MCF'], errors='coerce').fillna(0)

# --- WASTE ---
df_waste.rename(columns={'OGRID': 'Operator_ID', 'Volume_MCF': 'waste_mcf'}, inplace=True)
df_waste['Year'] = pd.to_numeric(df_waste['Year'], errors='coerce')
df_waste['Month'] = pd.to_numeric(df_waste['Month'], errors='coerce')
df_waste['Operator_ID'] = pd.to_numeric(df_waste['Operator_ID'], errors='coerce')
df_waste['waste_mcf'] = pd.to_numeric(df_waste['waste_mcf'], errors='coerce').fillna(0)

# --- BENEFICIAL USE ---
df_ben_use.rename(columns={'ogrid': 'Operator_ID', 'reporting_period_year': 'Year', 'reporting_period_month': 'Month', 'volume': 'ben_use_mcf'}, inplace=True)
df_ben_use['Year'] = pd.to_numeric(df_ben_use['Year'], errors='coerce')
df_ben_use['Month'] = pd.to_numeric(df_ben_use['Month'], errors='coerce')
df_ben_use['Operator_ID'] = pd.to_numeric(df_ben_use['Operator_ID'], errors='coerce')
df_ben_use['ben_use_mcf'] = pd.to_numeric(df_ben_use['ben_use_mcf'], errors='coerce').fillna(0)

# Drop any unparseable rows
for df in [df_prod, df_sales, df_waste, df_ben_use]:
    df.dropna(subset=['Operator_ID', 'Year', 'Month'], inplace=True)


# ==========================================
# 3. AGGREGATE TO OPERATOR-LEVEL (OGRID / YEAR / MONTH)
# ==========================================
print("Aggregating to the Operator level...")
prod_agg = df_prod.groupby(['Operator_ID', 'Year', 'Month'])['gas_vol'].sum().reset_index()
sales_agg = df_sales.groupby(['Operator_ID', 'Year', 'Month'])['Gas_Sold_MCF'].sum().reset_index()
waste_agg = df_waste.groupby(['Operator_ID', 'Year', 'Month'])['waste_mcf'].sum().reset_index()
ben_agg = df_ben_use.groupby(['Operator_ID', 'Year', 'Month'])['ben_use_mcf'].sum().reset_index()


# ==========================================
# 4. THE 4-WAY MASS BALANCE MERGE
# ==========================================
print("Executing 4-way mass balance merge...")
df_master = prod_agg.merge(sales_agg, on=['Operator_ID', 'Year', 'Month'], how='left')
df_master = df_master.merge(waste_agg, on=['Operator_ID', 'Year', 'Month'], how='left')
df_master = df_master.merge(ben_agg, on=['Operator_ID', 'Year', 'Month'], how='left')

# Temporarily fill NaNs with 0 to allow math operations
df_master.fillna(0, inplace=True)


# ==========================================
# 5. THE REGIME SHIFT FIX (HANDLING PRE-2021 GAPS)
# ==========================================
print("Applying econometric regime shift fixes for legacy data...")

# 5a. Isolate the strict regulatory regime (2021-2026)
df_modern = df_master[df_master['Year'] >= 2021].copy()

# Calculate Physics & Mass Balance
df_modern['accounted_gas'] = df_modern['Gas_Sold_MCF'] + df_modern['waste_mcf'] + df_modern['ben_use_mcf']
df_modern['shrinkage_mcf'] = df_modern['gas_vol'] - df_modern['accounted_gas']
df_modern['shrinkage_pct'] = np.where(
    df_modern['gas_vol'] > 0, 
    (df_modern['shrinkage_mcf'] / df_modern['gas_vol']) * 100, 
    0
)
# A company selling/wasting more gas than they physically pull out of the ground is a violation
df_modern['mass_balance_violation'] = df_modern['shrinkage_mcf'] < 0

# Calculate Flaring Intensity directly for the Quant models
df_modern['flaring_intensity_pct'] = np.where(
    df_modern['gas_vol'] > 0,
    (df_modern['waste_mcf'] / df_modern['gas_vol']) * 100,
    0
)

# 5b. Isolate legacy data (2015-2020) and protect it with NaNs
df_legacy = df_master[df_master['Year'] < 2021].copy()

df_legacy['waste_mcf'] = np.nan
df_legacy['ben_use_mcf'] = np.nan
df_legacy['accounted_gas'] = np.nan
df_legacy['shrinkage_mcf'] = np.nan 
df_legacy['shrinkage_pct'] = np.nan
df_legacy['flaring_intensity_pct'] = np.nan
df_legacy['mass_balance_violation'] = False 

# 5c. Recombine the master time-series
df_reconciled = pd.concat([df_legacy, df_modern], ignore_index=True)
df_reconciled.sort_values(by=['Operator_ID', 'Year', 'Month'], inplace=True)

# Save the final analytical dataset
output_master = os.path.join(project_root, 'data/processed/nm_operator_mass_balance_panel.csv')
os.makedirs(os.path.dirname(output_master), exist_ok=True)
df_reconciled.to_csv(output_master, index=False)


# ==========================================
# 6. DIAGNOSTIC REPORT
# ==========================================
print("\n==================================================")
print("--- OPERATOR MASS BALANCE REPORT (2021-2026) ---")
print("==================================================")
print(f"Total Operator-Months Analyzed: {len(df_modern):,}")
print(f"Total Gas Produced (MCF): {df_modern['gas_vol'].sum():,.0f}")
print(f"Total Gas Sold (MCF): {df_modern['Gas_Sold_MCF'].sum():,.0f}")
print(f"Total Flared/Vented (MCF): {df_modern['waste_mcf'].sum():,.0f}")

violations = df_modern['mass_balance_violation'].sum()
print(f"\nReporting Violations (Accounted > Produced): {violations:,} Operator-Months")
print(f"Average System Shrinkage: {df_modern['shrinkage_pct'].mean():.2f}%")

if violations > 0:
    print("\n--- TOP 5 REGULATORY VIOLATIONS (By Volume Discrepancy) ---")
    bad_actors = df_modern[df_modern['mass_balance_violation'] == True].copy()
    bad_actors['violation_size_mcf'] = bad_actors['shrinkage_mcf'] * -1
    print(bad_actors[['Operator_ID', 'Year', 'Month', 'gas_vol', 'accounted_gas', 'violation_size_mcf']].sort_values(by='violation_size_mcf', ascending=False).head())

print(f"\nFinal unified panel saved to: {output_master}")
