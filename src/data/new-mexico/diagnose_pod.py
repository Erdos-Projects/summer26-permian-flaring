import os
from collections import Counter
from lxml import etree as ET

# Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_xml = os.path.join(project_root, 'data/raw/new-mexico/podvolume.xml')

ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}podvolume"

print(f"Scanning the first 1,000,000 rows of {input_xml}...")

# Counters to see what actually exists in the data
disposition_codes = Counter()
years = Counter()
product_kinds = Counter()

count = 0
MAX_ROWS = 1000000

with open(input_xml, 'rb') as xml_file:
    context = ET.iterparse(xml_file, events=('end',))
    _, root = next(context) 

    for event, elem in context:
        if elem.tag == row_tag:
            
            # Extract test fields safely
            disp_node = elem.find(f'{ns}dispn_cde')
            yr_node = elem.find(f'{ns}sale_yr_num')
            prd_node = elem.find(f'{ns}prd_knd_cde')
            
            disp_str = disp_node.text.strip() if disp_node is not None and disp_node.text else "NONE"
            yr_str = yr_node.text.strip() if yr_node is not None and yr_node.text else "NONE"
            prd_str = prd_node.text.strip() if prd_node is not None and prd_node.text else "NONE"
            
            # Tally them up
            disposition_codes[disp_str] += 1
            years[yr_str] += 1
            product_kinds[prd_str] += 1
            
            count += 1
            
            # Clear memory
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
                
            if count >= MAX_ROWS:
                break

print("\n--- DIAGNOSTIC RESULTS (1M Rows) ---")
print("\nTop Disposition Codes found:")
for code, freq in disposition_codes.most_common():
    print(f"  Code '{code}': {freq:,} rows")

print("\nTop Years found:")
for year, freq in years.most_common(10):
    print(f"  Year '{year}': {freq:,} rows")

print("\nProduct Kinds found:")
for prd, freq in product_kinds.most_common():
    print(f"  Product '{prd}': {freq:,} rows")
