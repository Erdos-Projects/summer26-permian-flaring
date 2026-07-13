#!/usr/bin/env python3
"""
Concatenate all CSV files in a directory into a single combined CSV.

Assumes the files share a schema (or at least align by column name -- pandas will
union columns and fill missing ones with NaN if they don't).
"""
from pathlib import Path
import argparse
import pandas as pd


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", type=Path, help="folder containing CSVs to combine")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="output CSV path (default: <input_dir>/combined_output.csv)")
    ap.add_argument("--glob", default="*.csv", help="filename pattern (default: *.csv)")
    args = ap.parse_args()

    output_file = args.output or (args.input_dir / "combined_output.csv")

    files = sorted(args.input_dir.glob(args.glob))
    # Don't fold a previous run's output back into the input.
    files = [f for f in files if f.resolve() != output_file.resolve()]
    if not files:
        raise SystemExit(f"no files matching {args.glob} in {args.input_dir}")

    print(f"Found {len(files)} CSV files. Combining...")

    combined_df = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_file, index=False)

    print(f"Done! Saved as '{output_file}' with {len(combined_df)} rows.")


if __name__ == "__main__":
    main()