import csv
import os
from lxml import etree as ET

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')

input_xml = os.path.join(project_root, 'data/raw/new-mexico/wcproduction.xml')

# Define the new output directory and file
output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'nm_wcproduction_filtered.csv')

# Ensure the new interim/new-mexico/ directory exists to prevent a FileNotFoundError
os.makedirs(output_dir, exist_ok=True)

# Define the MS SQL namespace
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}wcproduction"

print(f"Reading from: {input_xml}")
print(f"Writing to: {output_csv}")
print("Starting streaming extraction (filtering for Lea/Eddy counties and O/G only)...")

# 2. Open CSV for writing
with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    
    # Write a "Long" format header
    csvwriter.writerow(['API_Number', 'Year', 'Month', 'Product_Kind', 'Volume'])

    # 3. Open the XML file in BINARY MODE ('rb') for lxml
    with open(input_xml, 'rb') as xml_file:
        context = ET.iterparse(xml_file, events=('end',))
        
        # Capture the root to clear it later
        _, root = next(context) 

        # 4. Iterate through the file
        for event, elem in context:
            
            if elem.tag == row_tag:
                
                # Extract County Code first to fail-fast and save massive processing time
                cnty_node = elem.find(f'{ns}api_cnty_cde')
                cnty_str = cnty_node.text.strip() if cnty_node is not None and cnty_node.text else ""
                
                # Check if County is Lea ('25') or Eddy ('15')
                if cnty_str in ['25', '15', '015', '025']:
                    
                    # Extract Product Kind early to filter out Water ('W')
                    knd_node = elem.find(f'{ns}prd_knd_cde')
                    prd_kind = knd_node.text.strip() if knd_node is not None and knd_node.text else "" 
                    
                    if prd_kind in ['O', 'G']:
                        
                        # Extract State and Well IDs to rebuild the API
                        st_node = elem.find(f'{ns}api_st_cde')
                        well_node = elem.find(f'{ns}api_well_idn')
                        
                        st_str = st_node.text.strip() if st_node is not None and st_node.text else "0"
                        well_str = well_node.text.strip() if well_node is not None and well_node.text else "0"
                        
                        # Reconstruct the standard 10-digit API (e.g., 30-025-20178)
                        try:
                            api_formatted = f"{int(st_str):02d}-{int(cnty_str):03d}-{int(well_str):05d}"
                        except ValueError:
                            api_formatted = f"{st_str}-{cnty_str}-{well_str}"
                        
                        # Extract date and production values
                        yr_node = elem.find(f'{ns}prodn_yr')
                        mth_node = elem.find(f'{ns}prodn_mth')
                        amt_node = elem.find(f'{ns}prod_amt')
                        
                        year = yr_node.text.strip() if yr_node is not None and yr_node.text else ""
                        month = mth_node.text.strip() if mth_node is not None and mth_node.text else ""
                        prod_amt = amt_node.text.strip() if amt_node is not None and amt_node.text else "0"
                        
                        # Write the row
                        csvwriter.writerow([api_formatted, year, month, prd_kind, prod_amt])

                # CRITICAL MEMORY STEP: Clear the element from RAM
                elem.clear()
                
                # Clear references to previous elements to prevent memory leaks
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

print("Extraction complete. Delaware Basin production data is ready.")
