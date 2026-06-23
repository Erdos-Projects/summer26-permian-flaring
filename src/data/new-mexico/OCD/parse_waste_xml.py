import csv
import os
from lxml import etree as ET

# 1. Setup paths using the Cookiecutter directory structure
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')

# Input from raw data
input_xml = os.path.join(project_root, 'data/raw/new-mexico/OCD/upstreamnaturalgaswaste.xml')

# Output to interim data
output_csv = os.path.join(project_root, 'data/interim/new-mexico/nm_upstream_waste_nonzero.csv')

# Define the MS SQL namespace
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}upstreamnaturalgaswaste"

print(f"Reading from: {input_xml}")
print(f"Writing to: {output_csv}")
print("Starting streaming extraction (filtering for Volume > 0)...")

# 2. Open CSV for writing
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    
    # Write the header row
    csvwriter.writerow([
        'Year', 'Month', 'OGRID', 'Structure_Type', 
        'Structure_ID', 'Waste_Type', 'Reporting_Category', 
        'Volume_MCF', 'Method'
    ])

    # 3. Open the XML file in BINARY MODE ('rb')
    # lxml handles UTF-16 decoding automatically when reading raw bytes
    with open(input_xml, 'rb') as xml_file:
        context = ET.iterparse(xml_file, events=('end',))

        # 4. Iterate through the file
        for event, elem in context:
            
            if elem.tag == row_tag:
                
                # Extract Volume first to fail-fast
                vol_node = elem.find(f'{ns}volume')
                vol_str = vol_node.text.strip() if vol_node is not None and vol_node.text else "0"
                
                # OPTIMIZATION: Only process and save the row if gas was actually wasted
                if vol_str != "0":
                    
                    # Extract the rest of the nodes
                    yr_node = elem.find(f'{ns}reporting_period_year')
                    mo_node = elem.find(f'{ns}reporting_period_month')
                    ogrid_node = elem.find(f'{ns}ogrid')
                    st_type_node = elem.find(f'{ns}structure_type')
                    st_id_node = elem.find(f'{ns}structure_id')
                    waste_node = elem.find(f'{ns}waste_type')
                    cat_node = elem.find(f'{ns}reporting_category')
                    meth_node = elem.find(f'{ns}determination_method')
                    
                    # Get text values safely
                    yr = yr_node.text.strip() if yr_node is not None and yr_node.text else ""
                    mo = mo_node.text.strip() if mo_node is not None and mo_node.text else ""
                    ogrid = ogrid_node.text.strip() if ogrid_node is not None and ogrid_node.text else ""
                    st_type = st_type_node.text.strip() if st_type_node is not None and st_type_node.text else ""
                    st_id = st_id_node.text.strip() if st_id_node is not None and st_id_node.text else ""
                    waste_type = waste_node.text.strip() if waste_node is not None and waste_node.text else ""
                    category = cat_node.text.strip() if cat_node is not None and cat_node.text else ""
                    method = meth_node.text.strip() if meth_node is not None and meth_node.text else ""
                    
                    # Write the non-zero row to the CSV
                    csvwriter.writerow([yr, mo, ogrid, st_type, st_id, waste_type, category, vol_str, method])

                # CRITICAL MEMORY STEP: Clear the element from RAM
                elem.clear()
                
                # Clear references to previous elements to prevent memory leaks
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

print("Extraction complete. Zero-volume rows dropped.")
