import os
import re
from collections import Counter

# 1. Setup
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
input_xml = os.path.join(project_root, 'data/raw/new-mexico/podvolume.xml')

# Jump to the last 100 MB of the massive file
file_size = os.path.getsize(input_xml)
chunk_size = 100 * 1024 * 1024 

print(f"Reading the last 100MB of the file...")

with open(input_xml, 'rb') as f:
    f.seek(file_size - chunk_size)
    raw_bytes = f.read()

print("Decoding UTF-16 bytes...")
# Using errors='ignore' in case our 100MB slice cuts a character in half
text = raw_bytes.decode('utf-16', errors='ignore')

print("Extracting Gas Disposition Codes...")
# Regex to find the Year, Product Kind, and Disposition Code
pattern = re.compile(
    r'<sale_yr_num>(\d{4})</sale_yr_num>\s*'
    r'<prd_knd_cde>([A-Z])\s*</prd_knd_cde>.*?'
    r'<dispn_cde>([A-Z])</dispn_cde>', 
    re.DOTALL
)

matches = pattern.findall(text)

gas_codes = Counter()
years = Counter()

for yr, prd, disp in matches:
    if prd == 'G':
        gas_codes[disp] += 1
        years[yr] += 1

print("\n--- RECENT GAS DISPOSITION CODES (Last 100MB) ---")
for code, freq in gas_codes.most_common():
    print(f"Code '{code}': {freq:,} records")

print("\n--- RECENT YEARS FOUND ---")
for yr, freq in years.most_common(5):
    print(f"Year '{yr}': {freq:,} records")
