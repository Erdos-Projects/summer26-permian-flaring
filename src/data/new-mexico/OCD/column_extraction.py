import argparse
import os
from lxml import etree

def detect_encoding(file_path):
    """Reads the first 4 bytes of the file to look for a UTF-16 Byte Order Mark (BOM)."""
    with open(file_path, 'rb') as f:
        bom = f.read(4)
    if bom.startswith(b'\xff\xfe') or bom.startswith(b'\xfe\xff'):
        return 'utf-16'
    return 'utf-8'

def extract_generic_schema(xml_path):
    """Streams any large XML file, captures its inline schema definitions, and exits early."""
    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"The file '{xml_path}' does not exist.")

    encoding = detect_encoding(xml_path)
    print(f"Detected File Encoding: {encoding}")
    print("Scanning for inline XML schema structure...")

    columns = {}
    col_stack = []
    inside_sequence = False

    # Stream the file using iterparse
    context = etree.iterparse(xml_path, events=('start', 'end'), encoding=encoding)

    for event, elem in context:
        # Strip out any namespace URLs to get the clean local tag name (e.g., 'element', 'sequence')
        tag_local = elem.tag.split('}')[-1]

        if event == 'start':
            # 1. Detect when we enter the layout definition block
            if tag_local == 'sequence':
                inside_sequence = True
            
            # 2. Capture any element defined inside the layout sequence
            elif tag_local == 'element' and inside_sequence:
                name = elem.attrib.get('name')
                if name:
                    # Default to 'unknown' if the type isn't defined as an attribute immediately
                    dtype = elem.attrib.get('type', 'unknown')
                    columns[name] = dtype
                    col_stack.append(name) # Track active elements to handle nested types
            
            # 3. Catch complex or restricted types (like lengths or specific data boundaries)
            elif tag_local == 'restriction' and inside_sequence and col_stack:
                base_type = elem.attrib.get('base')
                if base_type:
                    # Update the data type of the currently active column
                    current_col = col_stack[-1]
                    columns[current_col] = base_type

        elif event == 'end':
            # If a column tag closes, remove it from our tracking stack
            if tag_local == 'element' and inside_sequence and col_stack:
                col_stack.pop()
            
            # Once the main schema layout sequence ends, we have everything we need.
            # Break immediately so we don't scan the remaining 50 GB of data.
            elif tag_local == 'sequence':
                inside_sequence = False
                break

        # Constantly free up memory
        elem.clear()

    return columns

def main():
    parser = argparse.ArgumentParser(
        description="Stream any large XML file and generically extract columns & data types from its inline schema."
    )
    parser.add_argument("xml_file", help="Path to the target XML file")
    args = parser.parse_args()

    try:
        schema_results = extract_generic_schema(args.xml_file)
        
        if not schema_results:
            print("\nResult: No structural schema block found at the beginning of this file.")
            print("Ensure the XML file contains an embedded XSD schema (<xs:schema>).")
            return

        # Print the final output cleanly
        print(f"\n{'COLUMN NAME':<25} | {'DATA TYPE'}")
        print("-" * 50)
        for col_name, data_type in schema_results.items():
            print(f"{col_name:<25} | {data_type}")
        print(f"\nTotal Columns Discovered: {len(schema_results)}")

    except Exception as e:
        print(f"An error occurred while processing: {e}")

if __name__ == "__main__":
    main()