import pandas as pd
import os

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_csv = os.path.join(project_root, 'data/raw/new-mexico/OCD/New_Mexico_OCD_Oil_and_Gas_Wells.csv')
output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'nm_wells_spatial.csv')

os.makedirs(output_dir, exist_ok=True)

print(f"Reading from: {input_csv}")

# 2. Define the exact columns needed for the spatial merge
# This prevents Pandas from loading unnecessary heavy text columns (like URL links or giant geometry shapes)
columns_to_keep = [
    'id',           # The API Number
    'ogrid',        # The Operator ID
    'type',         # Gas or Oil well
    'status',       # Active, Plugged, etc.
    'county_code',  # Useful for Permian filtering
    'latitude', 
    'longitude'
]

# Read the CSV with explicitly forced string types for IDs to prevent dropping leading zeros
df_wells = pd.read_csv(
    input_csv, 
    usecols=columns_to_keep, 
    dtype={'id': str, 'ogrid': str, 'county_code': str}
)

# 3. Standardize column names to match the rest of your pipeline
df_wells.rename(columns={
    'id': 'API_Number',
    'ogrid': 'Operator_ID',
    'type': 'Well_Type',
    'status': 'Well_Status',
    'county_code': 'County_Code',
    'latitude': 'Latitude',
    'longitude': 'Longitude'
}, inplace=True)

# 4. Optional: Filter for the Permian Basin (Lea, Eddy, Chaves and Roosevelt Counties)
# (Codes 15 = Eddy, 25 = Leam, 05 = Chaves, 41 = Roosevelt)
df_permian_wells = df_wells[df_wells['County_Code'].isin(['15', '25', '015', '025', '005', '05', '041', '41'])].copy()

# 5. Export
print(f"Extraction complete.")
print(f"Total Permian Wells Extracted: {len(df_permian_wells):,}")
print(f"Writing to: {output_csv}")

df_permian_wells.to_csv(output_csv, index=False)
