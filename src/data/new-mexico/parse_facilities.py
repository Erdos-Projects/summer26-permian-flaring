import csv
import os
from lxml import etree as ET

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_xml = os.path.join(project_root, 'data/raw/new-mexico/facility.xml')
output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'nm_facilities.csv')

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# 2. Define namespace and tag structures
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}facility"

columns = [
    'id', 'name', 'type_code', 'type', 'status_code', 'status',
    'ogrid', 'ogrid_name', 'district_code', 'district', 'county_code',
    'county', 'ulstr', 'latitude', 'longitude', 'effective_date', 'last_edited_on'
]

print(f"Reading from: {input_xml}")
print(f"Writing to: {output_csv}")
print("Extracting facility data...")

# 3. Stream and extract
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(columns)

    # Open XML in binary mode for lxml iterparse
    with open(input_xml, 'rb') as xml_file:
        context = ET.iterparse(xml_file, events=('end',))
        
        # Skip the root element setup
        try:
            _, root = next(context)
        except StopIteration:
            pass

        for event, elem in context:
            if elem.tag == row_tag:
                row_data = []
                
                # Extract text for each designated column safely
                for col in columns:
                    node = elem.find(f'{ns}{col}')
                    val = node.text.strip() if node is not None and node.text else ""
                    row_data.append(val)
                
                csvwriter.writerow(row_data)

                # 4. Aggressive Memory Management
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

print("Facility parsing complete.")
