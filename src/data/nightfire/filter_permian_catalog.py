#!/usr/bin/env python3
"""
Filter the EOG VNF multiyear catalog down to Permian Basin sites,
KEEPING ALL ORIGINAL COLUMNS, and append a few derived labels:
    flare_id    : alias of the catalog 'ID' (the download key)
    state       : 'NM' or 'TX' from the site centroid
    in_delaware : True if the site falls in the Delaware sub-basin box

Run this first; feed its output CSV to download_vnf_sites.py.

    python filter_permian_catalog.py
    python filter_permian_catalog.py --catalog <in.csv> --out <out.csv>
"""

import argparse
import pandas as pd

# ----------------------- FILTER SETTINGS: EDIT HERE -----------------------
LAT_MIN, LAT_MAX = 31.0, 33.5            # Permian bounding box
LON_MIN, LON_MAX = -104.5, -101.0
KEEP_ISO        = {"USA"}                 # set to None to keep all countries
KEEP_CATEGORIES = None                 # set to None to keep all categories
# Delaware sub-basin box (the DiD straddle region) -> in_delaware flag
DELA_LAT = (31.3, 32.6)
DELA_LON = (-104.5, -103.3)
# New Mexico rule for this corner: west of -103 longitude AND north of 32 latitude
NM_LON_MAX, NM_LAT_MIN = -103.0, 32.0
# Column names in the catalog
COL_ID, COL_LAT, COL_LON = "ID", "Latitude", "Longitude"
COL_ISO, COL_CAT = "ISO", "Category"
# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="multiyear_catalog_2012_2021_v20230525.csv")
    ap.add_argument("--out", default="permian_sites_full.csv")
    args = ap.parse_args()

    cat = pd.read_csv(args.catalog)
    n0 = len(cat)
    orig_cols = list(cat.columns)               # preserve original order/columns

    # spatial filter (bounding box)
    m = cat[COL_LAT].between(LAT_MIN, LAT_MAX) & cat[COL_LON].between(LON_MIN, LON_MAX)
    df = cat[m].copy()

    # optional country / category filters
    if KEEP_ISO is not None:
        df = df[df[COL_ISO].isin(KEEP_ISO)]
    if KEEP_CATEGORIES is not None:
        df = df[df[COL_CAT].isin(KEEP_CATEGORIES)]

    # derived labels (added AFTER the original columns; nothing dropped)
    df["flare_id"] = df[COL_ID]
    df["state"] = "TX"
    df.loc[(df[COL_LON] < NM_LON_MAX) & (df[COL_LAT] > NM_LAT_MIN), "state"] = "NM"
    df["in_delaware"] = (df[COL_LON].between(*DELA_LON) & df[COL_LAT].between(*DELA_LAT))

    df = df[orig_cols + ["flare_id", "state", "in_delaware"]]
    df = df.sort_values(["state", "flare_id"])
    df.to_csv(args.out, index=False)

    # transparency: report exactly what passed
    print(f"catalog rows in: {n0}")
    print(f"after Permian box: {int(m.sum())}")
    print(f"written to {args.out}: {len(df)} sites (all {len(orig_cols)} original cols + 3 derived)")
    print("\nby state:\n" + df.state.value_counts().to_string())
    print("\nby category:\n" + df[COL_CAT].value_counts(dropna=False).to_string())
    print("\nDelaware sub-basin by state:\n"
          + df[df.in_delaware].state.value_counts().to_string())


if __name__ == "__main__":
    main()
