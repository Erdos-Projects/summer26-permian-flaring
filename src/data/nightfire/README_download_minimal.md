# Permian VNF Flaring — Data Download Guide

Three stages: **filter → download → clean.** End state: a folder of cleaned,
oil-only per-site flaring series.

---


## 1. Folder setup

Put these four files in one folder:

```
./src/data/nightfire/

├── filter_permian_catalog.py
├── datadownload.py
├── clean_by_category.py
└── 
```

Put the following catalog file in the data folder:

```
./data/processed/nightfire

multiyear_catalog_2012_2021_v20230525.csv
```

```
The catalog file can be downloaded from the EOG website, URL: https://eogdata.mines.edu/wwwdata/downloads/VNF_multiyear_2012-2021/multiyear_catalog_2012_2021_v20230525.csv
```

You'll add `eog_cookie.txt` in Step 2. After a run the folder also contains
`permian_sites_full.csv` and the `vnf_sites/` data folder — the end state.

> Don't commit `eog_cookie.txt` or `vnf_sites/` to git.

---

## 2. Get your EOG session cookie

1. Log in to <https://eogdata.mines.edu> in your browser.
2. Open DevTools (F12) → **Network** tab.
3. Download any one file (or click any protected download link).
4. Right-click that request → **Copy → Copy as cURL**.
5. Paste it into a plain text editor and save as `eog_cookie.txt` in the folder.
   (Paste the whole cURL command if you like — the script extracts the cookie.)

The cookie expires after a few hours; if downloads start failing, repeat this
step with a fresh one and re-run.

---

## 3. Run, in order (from inside the folder)

**1. Filter the catalog to the Permian:**
```
python filter_permian_catalog.py
```
→ `permian_sites_full.csv` (~2,328 sites in the lat/long box).

**2. Download (~2,324 files; resumable):**
```
python datadownload.py --catalog ../../../data/processed/nightfire/permian_sites_full.csv --out ../../../data/processed/nightfire/vnf_sites --cookie-file eog_cookie.txt
```
Safe to interrupt and re-run — already-downloaded files are skipped. If the
cookie expires it stops cleanly; refresh `eog_cookie.txt` and run the same
command again. A few `404`s in the summary are normal.

**3. Remove non-oil sites:**
```
python clean_by_category.py --catalog ../../../data/processed/nightfire/permian_sites_full.csv --dir ../../../data/processed/nightfire/vnf_sites
```
→ moves refinery / power-plant / chemical files to `vnf_sites/_excluded/`.

**4. Aggregate monthly:**
```
python aggregate_vnf_monthly.py ../../../data/processed/nightfire/vnf_sites ../../../data/processed/nightfire/vnf_sites_aggregated
```
→ creates folder ../../../data/processed/nightfire/vnf_sites_aggregated with site wise monthly time series files.

**5. Aggregate monthly with cloud masks:**
```
python aggregate_vnf_monthly_with_cloud_mask.py ../../../data/processed/nightfire/vnf_sites ../../../data/processed/nightfire/vnf_sites_aggregated_with_cloud_mask
```
→ creates folder ../../../data/processed/nightfire/vnf_sites_aggregated_with_cloud_mask with site wise monthly time series files which have more granular cloud mask data.

**6. Create a single csv:**
```
python combinecsvs.py ../../../data/processed/nightfire/vnf_sites_aggregated
python combinecsvs.py ../../../data/processed/nightfire/vnf_sites_aggregated_with_cloud_mask
```
→ combines the sitewise csvs into one big csv file.

---

## End state

```
vnf_sites/
├── site_<id>_multiyear_vnf_series.csv   # ~2,324 oil-site series
├── _excluded/                           # non-oil sites, set aside
├── _manifest.csv                        # download status per id
└── _category_cleaning.csv               # what was moved
```
