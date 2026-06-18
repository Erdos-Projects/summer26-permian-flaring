import os
import requests
import pandas as pd
import io
import gc
from dotenv import load_dotenv

# ==========================================
# 1. SETUP & PATH CONFIGURATION
# ==========================================
load_dotenv()

project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
output_dir = os.path.join(project_root, 'data/raw/new-mexico/viirs/multiyear_catalog')

os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, 'permian_multiyear_profiles.csv')

eog_cookie = os.getenv("EOG_COOKIE")
if not eog_cookie:
    print("[!] CRITICAL ERROR: EOG_COOKIE not found in environment or .env file.")
    exit(1)

# ==========================================
# 2. EXTRACT UNIQUE TARGET SITES
# ==========================================
print("Reading local crosswalk records...")
site_ids = set()

for cw_file in ['nm_wells_to_eog_sites.csv', 'nm_facilities_to_eog_sites.csv']:
    cw_path = os.path.join(interim_dir, cw_file)
    if os.path.exists(cw_path):
        df_cw = pd.read_csv(cw_path)
        site_ids.update(df_cw['EOG_Site_ID'].dropna().unique().astype(int))

unique_site_ids = sorted(list(site_ids))
print(f"Identified {len(unique_site_ids)} unique EOG target sites.")

# ==========================================
# 3. STREAMING DOWNLOAD (FULL HISTORY)
# ==========================================
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.5 Safari/605.1.15",
    "Cookie": eog_cookie
}

if os.path.exists(output_file):
    os.remove(output_file)
    print(f"Cleared previous output file at: {output_file}")

header_written = False
total_rows_written = 0
TARGET_COLUMNS = ['site_id', 'date_mscan', 'lat_gmtco', 'lon_gmtco', 'temp_bb', 'rh']

print("\nStarting full historical download (2012-Present)...")
for idx, site_id in enumerate(unique_site_ids, 1):
    print(f"[{idx}/{len(unique_site_ids)}] Fetching Site {site_id}...", end="", flush=True)
    
    target_url = f"https://eogdata.mines.edu/wwwdata/downloads/vnf_profiles/profiles_multiyear/site_{site_id}_multiyear_vnf_series.csv"
    
    try:
        response = requests.get(target_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            df_site = pd.read_csv(io.StringIO(response.text))
            
            if not df_site.empty:
                df_site.columns = [str(c).strip().lower() for c in df_site.columns]
                df_site['site_id'] = site_id
                
                available_cols = [col for col in TARGET_COLUMNS if col in df_site.columns]
                df_site = df_site[available_cols]
                
                if 'rh' in df_site.columns:
                    df_site['rh'] = pd.to_numeric(df_site['rh'], errors='coerce')
                    df_site = df_site[df_site['rh'] < 999999]
                
                if 'date_mscan' in df_site.columns:
                    df_site['date_mscan'] = pd.to_datetime(df_site['date_mscan'], errors='coerce')
                    df_site = df_site.dropna(subset=['date_mscan'])
                    
                    # Expand time barrier back to the start of the VIIRS instrument (2012)
                    df_site = df_site[df_site['date_mscan'].dt.year >= 2012]
                    df_site = df_site.sort_values(by='date_mscan')
                
                if not df_site.empty:
                    kept_len = len(df_site)
                    total_rows_written += kept_len
                    
                    df_site.to_csv(output_file, mode='a', header=not header_written, index=False)
                    header_written = True
                    print(f" Appended {kept_len} clean rows.")
                else:
                    print(" Dropped (No valid historical rows).")
            else:
                print(" Empty CSV returned.")
                
        elif response.status_code == 404:
            print(" Not Found (404).")
        elif response.status_code in [401, 403]:
            print("\n[!] Authentication Failure: Your EOG cookie expired.")
            break
        else:
            print(f" Failed (HTTP {response.status_code}).")
            
    except Exception as e:
        print(f" Error: {str(e)}")
        
    finally:
        del response
        if 'df_site' in locals():
            del df_site
        
        if idx % 50 == 0:
            gc.collect()

print("\n" + "="*60)
print("     HISTORICAL EXTRACTION COMPLETE (2012-PRESENT)")
print("="*60)