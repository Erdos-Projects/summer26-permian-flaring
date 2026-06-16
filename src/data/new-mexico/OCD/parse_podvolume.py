import csv
import os
from lxml import etree as ET

# 1. Setup paths based on standard project structure
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')

# Input path (Massive 20GB legacy database)
input_xml = os.path.join(project_root, 'data/raw/new-mexico/podvolume.xml')

# Output path
output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'nm_gas_sold.csv')

os.makedirs(output_dir, exist_ok=True)

# Define the MS SQL namespace used in the XML
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}podvolume"

# 2. Stream and Extract Gas Sales
print(f"Streaming massive 20GB XML: {input_xml}")
print(f"Extracting 'Delivery' ('D') Gas volumes directly by Operator OGRID...")

row_count = 0
extracted_count = 0

with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    
    # 3. New Streamlined Header (No more API numbers or Well Counts!)
    csvwriter.writerow(['Operator_ID', 'Year', 'Month', 'Gas_Sold_MCF'])

    # Open XML in BINARY mode for lxml iterparse
    with open(input_xml, 'rb') as xml_file:
        context = ET.iterparse(xml_file, events=('end',))
        
        # Skip the root element setup
        try:
            _, root = next(context)
        except StopIteration:
            pass

        for event, elem in context:
            if elem.tag == row_tag:
                row_count += 1
                
                # Check for 'D' (Delivery/Sales) first to fail-fast
                disp_node = elem.find(f'{ns}dispn_cde')
                disp_str = disp_node.text.strip().upper() if disp_node is not None and disp_node.text else ""
                
                if disp_str == 'D':
                    # Ensure the product is Gas ('G')
                    prd_node = elem.find(f'{ns}prd_knd_cde')
                    prd_str = prd_node.text.strip().upper() if prd_node is not None and prd_node.text else ""
                    
                    if prd_str == 'G':
                        
                        # Extract the exact tags confirmed in the XML snippet
                        ogrid_node = elem.find(f'{ns}from_ogrid_cde')
                        yr_node = elem.find(f'{ns}sale_yr_num')
                        mth_node = elem.find(f'{ns}sale_mth_num')
                        amt_node = elem.find(f'{ns}dispn_amt')
                        
                        operator_id = ogrid_node.text.strip() if ogrid_node is not None and ogrid_node.text else "0"
                        year = yr_node.text.strip() if yr_node is not None and yr_node.text else ""
                        month = mth_node.text.strip() if mth_node is not None and mth_node.text else ""
                        volume = amt_node.text.strip() if amt_node is not None and amt_node.text else "0"
                        
                        # Write the clean row directly to CSV
                        csvwriter.writerow([operator_id, year, month, volume])
                        extracted_count += 1

                # 4. CRITICAL MEMORY MANAGEMENT
                # Clear the element and delete previous siblings to maintain a flat memory profile
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]
                
                # Print a heartbeat to the terminal so you know it hasn't frozen
                if row_count % 5000000 == 0:
                    print(f"Scanned {row_count:,} rows... Extracted {extracted_count:,} sales records.")

print("\n--- EXTRACTION COMPLETE ---")
print(f"Total Rows Scanned: {row_count:,}")
print(f"Total Sales Records Saved: {extracted_count:,}")
print(f"Data saved to: {output_csv}")
