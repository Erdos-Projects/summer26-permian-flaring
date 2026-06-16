import pandas as pd
import matplotlib.pyplot as plt
import os

# Load the file
output_csv = os.path.expanduser('~/work/projects/summer26-permian-flaring/data/interim/new-mexico/nm_upstream_waste_nonzero.csv')
df = pd.read_csv(output_csv)

# --- CHECK 1: Basic Integrity ---
print("--- Data Summary ---")
print(f"Total non-zero flaring records: {len(df)}")
print(df.info())
print("\nFirst 5 rows:")
print(df.head())

# --- CHECK 2: Trend Analysis ---
# Convert Year/Month to a Datetime for plotting
df['Date'] = pd.to_datetime(df[['Year', 'Month']].assign(Day=1))

# Aggregate by month to see the flaring trend
monthly_flaring = df.groupby('Date')['Volume_MCF'].sum()

print("\n--- Monthly Flaring Totals (MCF) ---")
print(monthly_flaring.tail(10))

# --- CHECK 3: Category Breakdown ---
print("\n--- Flaring by Reporting Category ---")
print(df.groupby('Reporting_Category')['Volume_MCF'].sum().sort_values(ascending=False))

# Optional Plot
monthly_flaring.plot(kind='line', title='Total Monthly Flaring Volume (MCF)')
plt.ylabel('Volume (MCF)')
plt.show()
