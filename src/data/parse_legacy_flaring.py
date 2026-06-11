import csv
import os
from collections import defaultdict
from lxml import etree as ET

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')

mapping_csv = os.path.join(project_root, 'data/interim/new-mexico/nm_pod_to_api_mapping.csv')
input_xml = os.path.join(project_root, 'data/raw/new-mexico/podvolume.xml')
output_csv = os.path.join(project_root, 'data/interim/nm_legacy_flaring_2015_2020.csv')

# Define the MS SQL namespace
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}podvolume"

# 2. Load the Mapping Dictionary (The "Broadcast Join")
print(f"Loading POD-to-API mapping into memory...")
pod_to_apis = defaultdict(list)

with open(mapping_csv, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pod_to_apis[row['POD_ID']].append(row['API_Number'])

print(f"Loaded mappings for {len(pod_to_apis):,} unique PODs.")

# 3. Stream the Legacy Volumes
print(f"\nReading from: {input_xml}")
print(f"Writing to: {output_csv}")
print("Extracting Flaring ('F') and Venting ('V') volumes for 2015-2020...")

with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    # Adding Well_Count to prevent double-counting volumes later
    csvwriter.writerow(['API_Number', 'Year', 'Month', 'Volume_MCF', 'Disposition_Code', 'Well_Count'])

    with open(input_xml, 'rb') as xml_file:
        context = ET.iterparse(xml_file, events=('end',))
        _, root = next(context) 

        for event, elem in context:
            if elem.tag == row_tag:
                
                # Check Disposition Code first (Fail-fast optimization)
                disp_node = elem.find(f'{ns}dispn_cde')
                disp_str = disp_node.text.strip().upper() if disp_node is not None and disp_node.text else ""
                
                # 'F' = Flaring, 'V' = Venting
                if disp_str in ['F', 'V']:
                    
                    # Check Year
                    yr_node = elem.find(f'{ns}sale_yr_num')
                    yr_str = yr_node.text.strip() if yr_node is not None and yr_node.text else "0"
                    year = int(yr_str) if yr_str.isdigit() else 0
                    
                    # We only want the pre-treatment DiD window (2015 up to 2020)
                    # 2021+ is handled by your new waste rule dataset
                    if 2015 <= year <= 2020:
                        
                        pod_node = elem.find(f'{ns}pod_idn')
                        pod_str = pod_node.text.strip() if pod_node is not None and pod_node.text else ""
                        
                        # Only process if this POD belongs to our Lea/Eddy mapping
                        if pod_str in pod_to_apis:
                            
                            mth_node = elem.find(f'{ns}sale_mth_num')
                            amt_node = elem.find(f'{ns}dispn_amt')
                            
                            month = mth_node.text.strip() if mth_node is not None and mth_node.text else ""
                            volume = amt_node.text.strip() if amt_node is not None and amt_node.text else "0"
                            
                            # Get the associated APIs and the count
                            associated_apis = pod_to_apis[pod_str]
                            well_count = len(associated_apis)
                            
                            # Write a row for each API tied to this flared volume
                            for api in associated_apis:
                                csvwriter.writerow([api, year, month, volume, disp_str, well_count])

                # CRITICAL MEMORY STEP
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

print("Extraction complete. Legacy flaring data is ready for the DiD panel.")
