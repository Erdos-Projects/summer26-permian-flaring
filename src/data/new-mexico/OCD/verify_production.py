import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_csv = os.path.join(project_root, 'data/interim/new-mexico/nm_wcproduction_filtered.csv')

print(f"Loading data from: {input_csv}...")
df = pd.read_csv(input_csv)

# --- CHECK 1: Basic Integrity & Data Types ---
print("\n--- Data Integrity Check ---")
print(f"Total raw rows (Long format): {len(df):,}")

# Force 'Volume' to numeric, dropping any weird string artifacts to NaN, then fill with 0
df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)

# Verify product kinds are strictly 'O' and 'G'
print(f"Unique Product Kinds: {df['Product_Kind'].unique()}")

# --- FEATURE EXTRACTION: Pivoting to Wide Format ---
print("\n--- Pivoting to Wide Format (Well-Month granularity) ---")
# This creates separate columns for Oil and Gas volumes
df_wide = df.pivot_table(
    index=['API_Number', 'Year', 'Month'], 
    columns='Product_Kind', 
    values='Volume', 
    aggfunc='sum'
).reset_index()

# Rename columns to remove the pivot multi-index formatting
df_wide.rename(columns={'O': 'Oil_BBL', 'G': 'Gas_MCF'}, inplace=True)

# Fill any completely missing months with 0 
df_wide['Oil_BBL'] = df_wide['Oil_BBL'].fillna(0)
df_wide['Gas_MCF'] = df_wide['Gas_MCF'].fillna(0)

print(f"Total well-months (Wide format): {len(df_wide):,}")

# --- OUTLIER CLEANING: The Wiping Method (Physical Limits Only) ---
print("\n--- Cleaning Outliers (Replacing typos with NaN) ---")

# The Physical Cap (Permian Basin limits)
# These represent absolute maximums for a single well in a single month
PHYSICAL_MAX_OIL = 2000000
PHYSICAL_MAX_GAS = 2000000

# Count before wiping
oil_phys_outliers = (df_wide['Oil_BBL'] > PHYSICAL_MAX_OIL).sum()
gas_phys_outliers = (df_wide['Gas_MCF'] > PHYSICAL_MAX_GAS).sum()

# Wipe the physical impossibilities (replace with NaN to preserve the row)
df_wide.loc[df_wide['Oil_BBL'] > PHYSICAL_MAX_OIL, 'Oil_BBL'] = np.nan
df_wide.loc[df_wide['Gas_MCF'] > PHYSICAL_MAX_GAS, 'Gas_MCF'] = np.nan

print(f"Wiped {oil_phys_outliers:,} impossible Oil records.")
print(f"Wiped {gas_phys_outliers:,} impossible Gas records.")

# --- 1. FEATURE EXTRACTION: Datetime creation ---
# We MUST create the 'Date' column first so the lag filter can use it
df_wide['Date'] = pd.to_datetime(df_wide[['Year', 'Month']].assign(Day=1))

# --- 2. TIME FILTERING: Removing Artifacts and Lag ---
print("\n--- Applying Time Filters ---")

# Filter A: Remove the ONGARD Migration Artifact
STUDY_START_YEAR = 1994 # Using 1994 based on your terminal output
initial_len = len(df_wide)
df_wide = df_wide[df_wide['Year'] >= STUDY_START_YEAR].copy()
print(f"Filtered out {initial_len - len(df_wide):,} historical records prior to {STUDY_START_YEAR}.")

# Filter B: Remove the Reporting Lag (The sudden drop at the end)
LAG_MONTHS = 2 
max_date = df_wide['Date'].max() # Now this will work!
safe_cutoff = max_date - pd.DateOffset(months=LAG_MONTHS)

initial_len = len(df_wide)
df_wide = df_wide[df_wide['Date'] <= safe_cutoff].copy()
print(f"Trimmed {initial_len - len(df_wide):,} incomplete records after {safe_cutoff.strftime('%Y-%m')}.")

# --- CHECK 2: Basin-Level Trends ---
print("\n--- Summary Statistics (Cleaned Data) ---")
# Using lambda to suppress scientific notation in the printout
print(df_wide[['Oil_BBL', 'Gas_MCF']].describe().apply(lambda s: s.apply('{0:.2f}'.format)))

# Aggregate to the Basin level (summing ignores NaNs safely)
basin_production = df_wide.groupby('Date')[['Oil_BBL', 'Gas_MCF']].sum()

min_date = df_wide['Date'].min().strftime('%Y-%m')
max_date = df_wide['Date'].max().strftime('%Y-%m')
unique_wells = df_wide['API_Number'].nunique()

print(f"\nTimeframe: {min_date} to {max_date}")
print(f"Total unique wells in subset: {unique_wells:,}")

# --- CHECK 3: Visual Verification ---
fig, ax1 = plt.subplots(figsize=(10, 5))

color = 'tab:green'
ax1.set_xlabel('Date')
ax1.set_ylabel('Oil Production (BBL)', color=color)
ax1.plot(basin_production.index, basin_production['Oil_BBL'], color=color, label='Oil')
ax1.tick_params(axis='y', labelcolor=color)

ax2 = ax1.twinx()  
color = 'tab:red'
ax2.set_ylabel('Gas Production (MCF)', color=color)  
ax2.plot(basin_production.index, basin_production['Gas_MCF'], color=color, label='Gas')
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Delaware Basin (NM) - Cleaned Total Production Over Time')
fig.tight_layout() 
plt.show()
