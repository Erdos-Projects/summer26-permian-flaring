import csv
import os
from lxml import etree as ET

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_xml = os.path.join(project_root, 'data/raw/new-mexico/podwc.xml')
output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'nm_pod_to_api_mapping.csv')

os.makedirs(output_dir, exist_ok=True)

# Define the MS SQL namespace
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}podwc"

print(f"Reading from: {input_xml}")
print(f"Writing mapping dictionary to: {output_csv}")
print("Extracting POD to API relationships...")

# To avoid writing millions of duplicate rows (since PODs stay active for decades),
# we will use a set to keep track of unique POD-to-API pairs.
seen_pairs = set()

# 2. Open CSV for writing
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['POD_ID', 'API_Number'])

    # 3. Open the XML file in BINARY MODE ('rb')
    with open(input_xml, 'rb') as xml_file:
        context = ET.iterparse(xml_file, events=('end',))
        
        _, root = next(context) 

        # 4. Iterate through the file
        for event, elem in context:
            if elem.tag == row_tag:
                
                pod_node = elem.find(f'{ns}pod_idn')
                pod_str = pod_node.text.strip() if pod_node is not None and pod_node.text else ""
                
                if pod_str:
                    st_node = elem.find(f'{ns}api_st_cde')
                    cnty_node = elem.find(f'{ns}api_cnty_cde')
                    well_node = elem.find(f'{ns}api_well_idn')
                    
                    st_str = st_node.text.strip() if st_node is not None and st_node.text else "0"
                    cnty_str = cnty_node.text.strip() if cnty_node is not None and cnty_node.text else "0"
                    well_str = well_node.text.strip() if well_node is not None and well_node.text else "0"
                    
                    # Reconstruct the standard 10-digit API
                    try:
                        api_formatted = f"{int(st_str):02d}-{int(cnty_str):03d}-{int(well_str):05d}"
                    except ValueError:
                        api_formatted = f"{st_str}-{cnty_str}-{well_str}"
                    
                    pair = (pod_str, api_formatted)
                    
                    # Only write the pair if we haven't seen it yet
                    if pair not in seen_pairs:
                        csvwriter.writerow(pair)
                        seen_pairs.add(pair)

                # CRITICAL MEMORY STEP
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

print(f"Extraction complete. Found {len(seen_pairs):,} unique POD-to-API links.")
