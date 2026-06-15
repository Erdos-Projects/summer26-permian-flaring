import pandas as pd
import requests
import os
import time
from datetime import datetime, timedelta
import sys
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

output_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_csv = os.path.join(output_dir, 'test_viirs_vnf.csv')
tracker_file = os.path.join(output_dir, 'test_processed_logs.txt')

os.makedirs(output_dir, exist_ok=True)

start_date = datetime(2021, 1, 1)
end_date = datetime(2021, 1, 3)

LAT_MIN, LAT_MAX = 31.9, 33.6
LON_MIN, LON_MAX = -105.0, -102.9

satellites = ['npp', 'j01', 'j02']

# ==========================================
# 2. LOAD STATE TRACKER
# ==========================================
processed_files = set()
if os.path.exists(tracker_file):
    with open(tracker_file, 'r') as f:
        processed_files = set(f.read().splitlines())

write_header = not os.path.exists(output_csv)

# ==========================================
# 3. EXTRACTION LOOP
# ==========================================
print(f"Starting VNF SMOKE TEST (3 Days Only)...")
print("-" * 60)

headers = {
    "Cookie": EOG_COOKIE,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
}

current_date = start_date
while current_date <= end_date:
    date_str = current_date.strftime('%Y%m%d')
    
    for sat in satellites:
        log_id = f"{date_str}_{sat}"
        
        if log_id in processed_files:
            continue
            
        filename = f"VNF_{sat}_d{date_str}_noaa_v30.csv.gz"
        url = f"https://eogdata.mines.edu/wwwdata/viirs_products/vnf/v30/{filename}"
        temp_file = os.path.join(output_dir, f'test_temp_{sat}.csv.gz')
        
        try:
            response = requests.get(url, headers=headers, stream=True)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' in content_type.lower():
                    print(f"\n[!] AUTH ERROR: Server returned HTML. EOG_COOKIE is invalid or expired.")
                    sys.exit(1)
                    
                downloaded_bytes = 0
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_bytes += len(chunk)
                            mb = downloaded_bytes / (1024 * 1024)
                            sys.stdout.write(f"\r[{date_str} | {sat.upper()}] Downloading... {mb:.1f} MB    ")
                            sys.stdout.flush()
                
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] Download complete. Filtering data...    ")
                sys.stdout.flush()
                
                target_columns = ['Lat_GMTCO', 'Lon_GMTCO', 'Date_Mscan', 'Temp_BB', 'Area_BB', 'RH', 'Methane_EQ', 'CO2_EQ']
                df_global = pd.read_csv(temp_file, compression='gzip', usecols=target_columns, low_memory=False)
                
                # Exclude 999999 fills to retain only analyzable data
                df_permian = df_global[
                    (df_global['Lat_GMTCO'] >= LAT_MIN) & 
                    (df_global['Lat_GMTCO'] <= LAT_MAX) & 
                    (df_global['Lon_GMTCO'] >= LON_MIN) & 
                    (df_global['Lon_GMTCO'] <= LON_MAX) &
                    (df_global['RH'] != 999999) & 
                    (df_global['Temp_BB'] != 999999)
                ].copy()
                
                df_permian['Satellite'] = sat
                df_permian.to_csv(output_csv, mode='a', header=write_header, index=False)
                write_header = False 
                
                with open(tracker_file, 'a') as tf:
                    tf.write(f"{log_id}\n")
                    processed_files.add(log_id)
                
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] SUCCESS: Extracted {len(df_permian)} valid flares.          \n")
                
            elif response.status_code == 404:
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] SUCCESS: Handled 404 gracefully (File missing).          \n")
            else:
                sys.stdout.write(f"\r[{date_str} | {sat.upper()}] HTTP ERROR {response.status_code}                   \n")
                
        except KeyboardInterrupt:
            print("\n\n[!] Smoke test manually interrupted.")
            sys.exit(0)
        except Exception as e:
            sys.stdout.write(f"\r[{date_str} | {sat.upper()}] FAILED: {str(e)[:50]}...                   \n")
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        time.sleep(1.5)

    current_date += timedelta(days=1)

print("-" * 60)
print(f"Smoke Test Complete. Check {output_csv} to verify the data.")