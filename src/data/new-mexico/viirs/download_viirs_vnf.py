import pandas as pd
import requests
import os
import time
from datetime import datetime, timedelta
import sys
import calendar
import io  # <-- Required for pure RAM processing
from dotenv import load_dotenv

# ==========================================
# 1. SETUP & CREDENTIALS
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')

env_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=env_path)

EOG_COOKIE = os.getenv('EOG_COOKIE')

if not EOG_COOKIE:
    raise ValueError("CRITICAL ERROR: EOG_COOKIE not found. Check your .env file.")

output_dir = os.path.join(project_root, 'data/raw/new-mexico/viirs')
output_csv = os.path.join(output_dir, 'nm_viirs_vnf_2021_2026.csv')
tracker_file = os.path.join(output_dir, 'processed_logs.txt')

os.makedirs(output_dir, exist_ok=True)

# Permian Basin Bounding Box
LAT_MIN, LAT_MAX = 31.9, 33.6
LON_MIN, LON_MAX = -105.0, -102.9

satellites = ['npp', 'j01', 'j02']

# ==========================================
# 2. INTERACTIVE CLI
# ==========================================
print("\n--- VIIRS NIGHTFIRE (VNF) DOWNLOADER (PURE RAM MODE) ---")
year_input = input("Enter the Year you want to download (e.g., 2021): ").strip()
month_input = input("Enter the Month (e.g., 01 for Jan), or press ENTER for the entire year: ").strip()

try:
    target_year = int(year_input)
    if month_input:
        target_month = int(month_input)
        start_date = datetime(target_year, target_month, 1)
        _, last_day = calendar.monthrange(target_year, target_month)
        end_date = datetime(target_year, target_month, last_day)
        print(f"\n[Target] {start_date.strftime('%B %Y')}")
    else:
        start_date = datetime(target_year, 1, 1)
        end_date = datetime(target_year, 12, 31)
        print(f"\n[Target] The entire year of {target_year}")
except ValueError:
    print("\n[!] Invalid input. Please enter numeric values.")
    sys.exit(1)

# ==========================================
# 3. LOAD STATE TRACKER
# ==========================================
processed_files = set()
if os.path.exists(tracker_file):
    with open(tracker_file, 'r') as f:
        processed_files = set(f.read().splitlines())

write_header = not os.path.exists(output_csv)

# ==========================================
# 4. EXTRACTION LOOP
# ==========================================
print(f"Starting VNF pipeline. Protecting SSD with in-memory streaming...")
print("-" * 60)

headers = {
    "Cookie": EOG_COOKIE,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.5 Safari/605.1.15"
}

# The expanded, highly targeted column list
target_columns = [
    'Lat_GMTCO', 'Lon_GMTCO', 'Date_Mscan', 
    'Temp_BB', 'Area_BB', 'RH', 'Methane_EQ', 'CO2_EQ',
    'Cloud_Mask', 'QF_Fit' # Added Quality and Cloud filters
]

current_date = start_date
while current_date <= end_date:
    date_str = current_date.strftime('%Y%m%d')
    
    for sat in satellites:
        log_id = f"{date_str}_{sat}"
        
        if log_id in processed_files:
            continue
            
        filename = f"VNF_{sat}_d{date_str}_noaa_v30.csv.gz"
        url = f"https://eogdata.mines.edu/wwwdata/viirs_products/vnf/v30/{filename}"
        
        try:
            response = requests.get(url, headers=headers, stream=True)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type.lower():
                    print(f"\n[!] AUTH ERROR: Server returned HTML. EOG_COOKIE is invalid/expired.")
                    sys.exit(1)
                    
                downloaded_bytes = 0
                
                # ---> THE RAM FIX: Create a virtual file in memory <---
                memory_file = io.BytesIO()
                
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        memory_file.write(chunk)
                        downloaded_bytes += len(chunk)
                        mb = downloaded_bytes / (1024 * 1024)
                        sys.stdout.write(f"\r[{date_str} | {sat.upper()}] RAM Download... {mb:.1f} MB    ")
                        sys.stdout.flush()
                
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] Download complete. Filtering in memory...    ")
                sys.stdout.flush()
                
                # Reset the virtual file pointer to the beginning so Pandas can read it
                memory_file.seek(0)
                
                # Load directly from RAM into Pandas
                df_global = pd.read_csv(memory_file, compression='gzip', usecols=target_columns, low_memory=False)
                
                # Close and clear the virtual file to free up RAM instantly
                memory_file.close() 
                
                # Spatial and Quality Filter
                df_permian = df_global[
                    (df_global['Lat_GMTCO'] >= LAT_MIN) & 
                    (df_global['Lat_GMTCO'] <= LAT_MAX) & 
                    (df_global['Lon_GMTCO'] >= LON_MIN) & 
                    (df_global['Lon_GMTCO'] <= LON_MAX) &
                    (df_global['RH'] != 999999) & 
                    (df_global['Temp_BB'] != 999999)
                ].copy()
                
                df_permian['Satellite'] = sat
                
                # This is the ONLY time the script touches your SSD (appending a few KB of local data)
                df_permian.to_csv(output_csv, mode='a', header=write_header, index=False)
                write_header = False 
                
                with open(tracker_file, 'a') as tf:
                    tf.write(f"{log_id}\n")
                    processed_files.add(log_id)
                
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] SUCCESS: Extracted {len(df_permian)} valid flares.          \n")
                
            elif response.status_code == 404:
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] CACHED 404: File missing/Offline.          \n")
                with open(tracker_file, 'a') as tf:
                    tf.write(f"{log_id}\n")
                    processed_files.add(log_id)
            else:
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] HTTP ERROR {response.status_code}                   \n")
                
        except KeyboardInterrupt:
            print("\n\n[!] Extraction manually interrupted.")
            sys.exit(0)
        except Exception as e:
            sys.stdout.write(f"\r[{date_str} | {sat.upper()}] FAILED: {str(e)[:50]}...                   \n")
        
        time.sleep(1.5)

    current_date += timedelta(days=1)

print("-" * 60)
print(f"Pipeline Completed for selected timeframe.")