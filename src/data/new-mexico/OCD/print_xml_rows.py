import argparse
import os
from lxml import etree
from tabulate import tabulate

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        bom = f.read(4)
    if bom.startswith(b'\xff\xfe') or bom.startswith(b'\xfe\xff'):
        return 'utf-16'
    return 'utf-8'

def print_first_rows(xml_path, max_rows=5):
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"The file '{xml_path}' does not exist.")

    encoding = detect_encoding(xml_path)
    print(f"Streaming data records (Encoding: {encoding})...")
    
    passed_schema = False
    inside_sequence = False
    ordered_columns = []
    
    row_tag_name = None
    current_row_data = {}
    all_rows = []

    context = etree.iterparse(xml_path, events=('start', 'end'), encoding=encoding)

    for event, elem in context:
        tag_local = elem.tag.split('}')[-1]

        # --- PHASE 1: Read the Schema to capture column order ---
        if not passed_schema:
            if event == 'start':
                if tag_local == 'sequence':
                    inside_sequence = True
                elif tag_local == 'element' and inside_sequence:
                    name = elem.attrib.get('name')
                    if name and name not in ordered_columns:
                        ordered_columns.append(name)
                        
            elif event == 'end':
                if tag_local == 'sequence':
                    inside_sequence = False
                elif tag_local == 'schema':
                    passed_schema = True
                elem.clear()
            continue

        # --- PHASE 2: Read the Data Rows ---
        if event == 'start':
            if row_tag_name is None and tag_local != 'root':
                row_tag_name = tag_local
                
        elif event == 'end':
            if row_tag_name and tag_local != row_tag_name and tag_local != 'root':
                val = elem.text.strip() if elem.text else ""
                current_row_data[tag_local] = val

            elif tag_local == row_tag_name:
                all_rows.append(current_row_data)
                current_row_data = {} 
                
                # Use the user-defined max_rows limit
                if len(all_rows) >= max_rows:
                    break

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

    if not all_rows:
        print("No data records found after the schema block.")
        return

    if not ordered_columns:
        print("Warning: No columns were found in the schema block. The table may be empty.")

    # --- FORMATTING THE TABLE ---
    table_data = []
    for row in all_rows:
        table_data.append([row.get(col, "") for col in ordered_columns])

    print(f"\n--- Displaying First {len(all_rows)} Rows of '{row_tag_name}' ---")
    print(tabulate(table_data, headers=ordered_columns, tablefmt="grid"))

def main():
    parser = argparse.ArgumentParser(description="Print a specified number of records from a large XML file using the schema's column order.")
    parser.add_argument("xml_file", help="Path to the XML file")
    
    # --- NEW ARGUMENT FOR ROW COUNT ---
    parser.add_argument(
        "-n", "--num-rows", 
        help="Number of rows to print (default is 5)", 
        type=int, 
        default=5
    )
    
    args = parser.parse_args()

    try:
        # Pass the parsed argument directly into the function
        print_first_rows(args.xml_file, max_rows=args.num_rows)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()