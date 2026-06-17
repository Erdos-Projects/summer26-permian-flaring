#!/usr/bin/env python3
"""
Post-download category cleaning.

The download stage stays purely spatial (every site in the lat-long box).
This step looks up each downloaded file's Category in the catalog and separates
out the ones you don't want to analyze (default: keep only 'oil'). By default it
MOVES them to an _excluded/ subfolder (non-destructive, reversible); pass
--delete to remove them instead. Re-runnable and idempotent.

  python clean_by_category.py --catalog permian_sites_full.csv --dir vnf_sites
  python clean_by_category.py --keep oil,upstream        # keep more categories
  python clean_by_category.py --delete                   # delete instead of move
"""

import argparse, csv, os, re, shutil

FNAME = re.compile(r"site_(\d+)_multiyear_vnf_series\.csv$")


def load_categories(catalog, id_col, cat_col):
    cats = {}
    with open(catalog, newline="") as f:
        for row in csv.DictReader(f):
            v = (row.get(id_col) or "").strip()
            if v:
                cats[int(float(v))] = (row.get(cat_col) or "").strip()
    return cats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="permian_sites_full.csv")
    ap.add_argument("--dir", default="vnf_sites")
    ap.add_argument("--id-col", default="flare_id")
    ap.add_argument("--cat-col", default="Category")
    ap.add_argument("--keep", default="oil", help="comma-separated categories to keep")
    ap.add_argument("--excluded-dir", default=None)
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()

    keep = {c.strip() for c in args.keep.split(",") if c.strip()}
    cats = load_categories(args.catalog, args.id_col, args.cat_col)
    excl_dir = args.excluded_dir or os.path.join(args.dir, "_excluded")
    if not args.delete:
        os.makedirs(excl_dir, exist_ok=True)

    kept = moved = unknown = 0
    actions = []
    for name in sorted(os.listdir(args.dir)):
        m = FNAME.search(name)
        if not m:
            continue                                  # skip _manifest.csv etc.
        sid = int(m.group(1))
        cat = cats.get(sid)
        if cat is None:
            unknown += 1
            actions.append((sid, name, "in_dir_not_in_catalog", ""))
            continue
        if cat in keep:
            kept += 1
            continue
        src = os.path.join(args.dir, name)
        if args.delete:
            os.remove(src); moved += 1
            actions.append((sid, name, "deleted", cat))
        else:
            shutil.move(src, os.path.join(excl_dir, name)); moved += 1
            actions.append((sid, name, "moved_to_excluded", cat))

    report = os.path.join(args.dir, "_category_cleaning.csv")
    with open(report, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["flare_id", "filename", "action", "category"])
        w.writerows(actions)

    verb = "deleted" if args.delete else f"moved to {excl_dir}"
    print(f"kept (categories {sorted(keep)}): {kept}")
    print(f"{verb}: {moved}")
    if unknown:
        print(f"WARNING: {unknown} downloaded files have no catalog match (logged in {report}).")
    for sid, name, action, cat in actions:
        if action != "in_dir_not_in_catalog":
            print(f"  site_{sid} [{cat}] -> {action}")
    if moved or unknown:
        print("details:", report)


if __name__ == "__main__":
    main()
