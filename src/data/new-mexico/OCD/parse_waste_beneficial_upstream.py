import csv
import os
from lxml import etree as ET

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_xml = os.path.join(project_root, 'data/raw/new-mexico/upstreamnaturalgaswastebeneficialuse.xml')
output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'nm_upstream_beneficial_use_nonzero.csv')

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# 2. Define namespace and tags
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}upstreamnaturalgaswastebeneficialuse"

columns = [
    'reporting_period_year', 'reporting_period_month', 'ogrid', 
    'structure_type', 'structure_id', 'use_type', 
    'use_type_other', 'volume', 'saved'
]

print(f"Reading from: {input_xml}")
print(f"Writing to: {output_csv}")
print("Extracting beneficial use data (filtering for Volume > 0)...")

# 3. Stream and extract
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(columns)

    # Open XML in binary mode for lxml iterparse
    with open(input_xml, 'rb') as xml_file:
        context = ET.iterparse(xml_file, events=('end',))
        
        # Skip the root element setup safely
        try:
            _, root = next(context)
        except StopIteration:
            pass

        for event, elem in context:
            if elem.tag == row_tag:
                
                # Extract Volume first to execute fail-fast optimization
                vol_node = elem.find(f'{ns}volume')
                vol_str = vol_node.text.strip() if vol_node is not None and vol_node.text else "0"
                
                if vol_str != "0":
                    row_data = []
                    
                    # Extract the rest of the columns
                    for col in columns:
                        if col == 'volume':
                            row_data.append(vol_str)
                        else:
                            node = elem.find(f'{ns}{col}')
                            val = node.text.strip() if node is not None and node.text else ""
                            row_data.append(val)
                    
                    csvwriter.writerow(row_data)

                # 4. Aggressive Memory Management
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

print("Beneficial use parsing complete. Zero-volume rows dropped.")
