#!/usr/bin/env python3
"""
Aggregate per-site VIIRS Nightfire (VNF) overpass time series to monthly per-site values.

Each input file is one row per satellite overpass of a site, with 999999 as the no-data
sentinel. This script produces RAW monthly aggregates only -- counts and additive/order
statistics. It deliberately does NO division: no means, no rates, no normalized signals.
Everything needed to build those downstream is present (sums + per-column counts).

For every calendar month it records:
  * observation accounting : total looks, detections vs non-detections, the full
                             cloud-mask breakdown (each mask value, split by detect/non-detect),
                             and per-satellite counts
  * intensity statistics   : over detections only -- sum, count (n), min, max for each measured
                             field. mean = sum / n is left for you to compute downstream.

Input  folder : one CSV per site (any name).
Output folder : same filenames, monthly-aggregated.
"""
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

# ----------------------------- CONFIG -----------------------------
SENTINEL  = 999999            # VNF no-data value
DATE_COL  = "Date_Mscan"      # the overpass timestamp
RH_COL    = "RH"              # presence of RH defines a "fitted" detection
CLOUD_COL = "Cloud_Mask"      # VIIRS cloud mask
SAT_COL   = "Satellite"

CLOUD_VALUES = [0, 1, 2, 3]   # mask values broken out individually (plus NA, handled separately)
SATELLITES   = ["SNPP", "NOAA-20"]   # broken out individually (plus OTHER)

# fields measured on a detection -> sum/n/min/max each. Add Rad_* bands here if you want them.
INTENSITY = ["RH", "RHI", "Flow_Rate", "Temp_BB", "Temp_Bkg", "ESF_BB", "Area_BB", "Area_Pixel"]
# ------------------------------------------------------------------


def aggregate_site(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=[DATE_COL])
    df["_month"] = df[DATE_COL].dt.to_period("M")

    det = df[RH_COL].notna()
    cm = df[CLOUD_COL]
    sat = df.get(SAT_COL, pd.Series(index=df.index, dtype=object))

    rows = []
    for m, idx in df.groupby("_month").groups.items():
        g = df.loc[idx]
        d = det.loc[idx]
        c = cm.loc[idx]
        s = sat.loc[idx]
        gd = g.loc[d]   # detection rows only

        rec = {
            "flare_id": g["flare_id"].iloc[0] if "flare_id" in g else np.nan,
            "year_month": str(m),
            "year": m.year,
            "month": m.month,
            "lat": g["Lat_GMTCO"].iloc[0] if "Lat_GMTCO" in g else np.nan,
            "lon": g["Lon_GMTCO"].iloc[0] if "Lon_GMTCO" in g else np.nan,
            # --- top-level observation counts ---
            "n_obs": len(g),
            "n_detect": int(d.sum()),
            "n_nondet": int((~d).sum()),
        }

        # --- cloud mask broken out by value, split detect / non-detect ---
        for v in CLOUD_VALUES:
            at_v = (c == v)
            rec[f"n_detect_cm{v}"] = int((d & at_v).sum())
            rec[f"n_nondet_cm{v}"] = int((~d & at_v).sum())
        na = c.isna()
        rec["n_detect_cmNA"] = int((d & na).sum())
        rec["n_nondet_cmNA"] = int((~d & na).sum())

        # --- per-satellite counts ---
        known = pd.Series(False, index=g.index)
        for name in SATELLITES:
            at = (s == name)
            known |= at
            tag = name.replace("-", "")
            rec[f"n_obs_{tag}"] = int(at.sum())
            rec[f"n_detect_{tag}"] = int((d & at).sum())
        rec["n_obs_OTHERSAT"] = int((~known).sum())
        rec["n_detect_OTHERSAT"] = int((d & ~known).sum())

        # --- intensity: detections only, sum / n / min / max (NO mean) ---
        for col in INTENSITY:
            if col not in g:
                continue
            vals = gd[col].dropna()
            lo = col.lower()
            rec[f"{lo}_sum"] = float(vals.sum())          # sum of nothing = 0.0
            rec[f"{lo}_n"]   = int(vals.size)             # count -> your divisor downstream
            rec[f"{lo}_min"] = float(vals.min()) if vals.size else np.nan
            rec[f"{lo}_max"] = float(vals.max()) if vals.size else np.nan

        rows.append(rec)

    return pd.DataFrame(rows).sort_values("year_month").reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", type=Path, help="folder of per-site VNF time-series CSVs")
    ap.add_argument("output_dir", type=Path, help="folder for monthly-aggregate CSVs")
    ap.add_argument("--glob", default="*.csv", help="filename pattern (default: *.csv)")
    args = ap.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(args.input_dir.glob(args.glob))
    if not files:
        raise SystemExit(f"no files matching {args.glob} in {args.input_dir}")

    n_ok = 0
    for f in files:
        try:
            df = pd.read_csv(f, na_values=[SENTINEL, str(SENTINEL)])
            if DATE_COL not in df.columns:
                print(f"  skip {f.name}: no '{DATE_COL}' column")
                continue
            out = aggregate_site(df)
            out.to_csv(args.output_dir / f.name, index=False)   # SAME filename
            n_ok += 1
            print(f"  {f.name}: {len(df)} overpasses -> {len(out)} months")
        except Exception as e:
            print(f"  ERROR {f.name}: {e}")
    print(f"done: {n_ok}/{len(files)} files -> {args.output_dir}")


if __name__ == "__main__":
    main()
