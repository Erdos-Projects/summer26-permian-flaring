import csv
import os
from lxml import etree as ET

# 1. Setup paths
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_xml = os.path.join(project_root, 'data/raw/new-mexico/OCD/wellhistory.xml')
output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'nm_wells.csv')

os.makedirs(output_dir, exist_ok=True)

# Define XML namespaces and row tag
ns = "{urn:schemas-microsoft-com:sql:SqlRowSet1}"
row_tag = f"{ns}wellhistory"

print(f"Reading from: {input_xml}")
print(f"Writing to: {output_csv}")
print("Starting streaming extraction for well history...")

with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
    csvwriter = csv.writer(csvfile)
    
    # Write the header
    csvwriter.writerow([
        'API_Number', 
        'OGRID', 
        'Well_Type', 
        'District', 
        'Latitude', 
        'Longitude', 
        'Well_Status', 
        'Spud_Date', 
        'Plug_Date'
    ])

    with open(input_xml, 'rb') as xml_file:
        # iterparse allows streaming the file without loading the whole XML into memory
        context = ET.iterparse(xml_file, events=('end',))
        
        try:
            _, root = next(context) 
        except StopIteration:
            pass

        # Helper function to extract text safely
        def get_tag_text(elem, tag_name, default=""):
            node = elem.find(f'{ns}{tag_name}')
            return node.text.strip() if node is not None and node.text else default

        for event, elem in context:
            if elem.tag == row_tag:
                
                # Reconstruct API Number
                st_str = get_tag_text(elem, 'api_st_cde', '30')
                cnty_str = get_tag_text(elem, 'api_cnty_cde', '0')
                well_str = get_tag_text(elem, 'api_well_idn', '0')
                
                try:
                    # Format as 00-000-00000
                    api_formatted = f"{int(st_str):02d}-{int(cnty_str):03d}-{int(well_str):05d}"
                except ValueError:
                    api_formatted = f"{st_str}-{cnty_str}-{well_str}"
                
                # Extract other requested fields
                ogrid = get_tag_text(elem, 'ogrid_cde')
                well_type = get_tag_text(elem, 'well_typ_cde')
                district = get_tag_text(elem, 'ocd_district') 
                latitude = get_tag_text(elem, 'latitude')
                longitude = get_tag_text(elem, 'longitude')
                well_status = get_tag_text(elem, 'status')
                spud_date = get_tag_text(elem, 'spud_dte')
                plug_date = get_tag_text(elem, 'plug_dte')

                # Write the row to CSV
                csvwriter.writerow([
                    api_formatted, 
                    ogrid, 
                    well_type, 
                    district, 
                    latitude, 
                    longitude, 
                    well_status, 
                    spud_date, 
                    plug_date
                ])

                # Memory Management: clear the parsed element
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

print("Well history extraction complete.")