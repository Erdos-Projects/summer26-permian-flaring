#!/usr/bin/env python3
"""
Download EOG VIIRS Nightfire per-site multiyear series.

EOG gates downloads. As of 2026-06-01, the OAuth2 *programmatic* path
(client_id/secret token) is limited to PAID SUBSCRIBERS. This script supports
two auth modes:

  (A) COOKIE mode  -- for browser/free accounts, NO client_id needed.
      Log in at eogdata.mines.edu, copy your session Cookie header from the
      browser (Network tab -> a download request -> Copy as cURL -> the Cookie:
      line), and export it:
          export EOG_COOKIE='cookie1=...; cookie2=...'
      If EOG_COOKIE is set, the script uses it and skips the token flow.

  (B) TOKEN mode   -- for paid subscribers with client credentials.
          export EOG_USERNAME=...  EOG_PASSWORD=...
          export EOG_CLIENT_ID=... EOG_CLIENT_SECRET=...
      The 5-minute token is refreshed automatically during the run.

Reads flare_id values from a catalog CSV and downloads
site_<id>_multiyear_vnf_series.csv each, with resume, retries, a concurrency
cap, and a _manifest.csv of every id's outcome.

SET BASE_URL (top of file) = the folder your site_20227 file came from.

Usage:
  python download_vnf_sites.py --catalog permian_sites_full.csv --out vnf_sites
  python download_vnf_sites.py --dry-run
"""

import argparse, csv, os, re, sys, time, random, threading, getpass
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests  # pip install requests

# ----------------------- CONFIG: EDIT THIS -----------------------
BASE_URL = "https://eogdata.mines.edu/wwwdata/downloads/vnf_profiles/profiles_multiyear/"   # folder your per-site files live in
FILENAME_TMPL = "site_{id}_multiyear_vnf_series.csv"
TOKEN_URL = "https://eogauth-new.mines.edu/realms/eog/protocol/openid-connect/token"
# -----------------------------------------------------------------


class CookieAuth:
    """Browser-session auth: reuse a logged-in Cookie header. No client_id."""
    def __init__(self, cookie):
        self._cookie = cookie
    def headers(self):
        return {"Cookie": self._cookie}
    def on_unauthorized(self):
        return False   # a cookie can't be refreshed; caller stops the run


class TokenAuth:
    """Subscriber auth: short-lived bearer token (~5 min) with auto-refresh."""
    def __init__(self, creds, skew=45):
        self._creds = creds
        self._skew = skew
        self._lock = threading.Lock()
        self._token = None
        self._expiry = 0.0
    def _fetch(self):
        r = requests.post(TOKEN_URL, data=self._creds, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"token request failed: HTTP {r.status_code} {r.text[:200]}")
        d = r.json()
        self._token = d["access_token"]
        self._expiry = time.time() + float(d.get("expires_in", 300))
    def _get(self, force=False):
        with self._lock:
            if force or self._token is None or time.time() > self._expiry - self._skew:
                self._fetch()
            return self._token
    def headers(self):
        return {"Authorization": "Bearer " + self._get()}
    def on_unauthorized(self):
        self._get(force=True)
        return True
    def warmup(self):
        self._get(force=True)


def build_url(site_id):
    return BASE_URL.rstrip("/") + "/" + FILENAME_TMPL.format(id=site_id)


def read_ids(catalog_csv, id_col):
    ids, seen = [], set()
    with open(catalog_csv, newline="") as f:
        for row in csv.DictReader(f):
            v = (row.get(id_col) or "").strip()
            if not v:
                continue
            n = int(float(v))
            if n not in seen:
                seen.add(n); ids.append(n)
    return ids


def download_one(session, auth, site_id, out_dir, timeout, retries, min_bytes, stop):
    path = os.path.join(out_dir, FILENAME_TMPL.format(id=site_id))
    if os.path.exists(path) and os.path.getsize(path) >= min_bytes:
        return (site_id, "skip", os.path.getsize(path), "")
    url = build_url(site_id)
    backoff = 2.0
    for _ in range(retries):
        if stop.is_set():
            return (site_id, "auth_stopped", 0, url)
        try:
            r = session.get(url, headers=auth.headers(), timeout=timeout)
            if r.status_code == 200 and len(r.content) >= min_bytes:
                head = r.content[:300].decode("utf-8", "replace")
                if "flare_id" not in head and "Date_Mscan" not in head:
                    return (site_id, "bad_content", len(r.content), url)
                tmp = path + ".part"
                with open(tmp, "wb") as fh:
                    fh.write(r.content)
                os.replace(tmp, path)
                return (site_id, "ok", len(r.content), "")
            if r.status_code in (401, 403):
                if auth.on_unauthorized():       # token refreshed -> retry
                    continue
                stop.set()                       # cookie stale -> halt the run cleanly
                return (site_id, "auth_error", 0, url)
            elif r.status_code == 404:
                return (site_id, "404", 0, url)
        except requests.RequestException:
            pass
        time.sleep(backoff + random.uniform(0, 1))
        backoff = min(backoff * 2, 30)
    return (site_id, "fail", 0, url)


def clean_cookie(raw):
    """Tolerate however the cookie was pasted: raw value, 'Cookie:' prefix,
    a whole 'copy as cURL' command, or one with stray newlines."""
    s = raw.strip()
    m = re.search(r"-H\s+['\"]?[Cc]ookie:\s*([^'\"]+)['\"]?", s)
    if m:
        return m.group(1).strip()
    m = re.search(r"-b\s+['\"]([^'\"]+)['\"]", s)
    if m:
        return m.group(1).strip()
    s = re.sub(r"^[Cc]ookie:\s*", "", s)
    return s.replace("\r", "").replace("\n", "").strip()


def make_auth(cookie_file=None):
    cookie_file = cookie_file or os.environ.get("EOG_COOKIE_FILE")
    raw = None
    if cookie_file:
        with open(cookie_file) as fh:
            raw = fh.read()
    elif os.environ.get("EOG_COOKIE"):
        raw = os.environ["EOG_COOKIE"]
    if raw:
        cookie = clean_cookie(raw)
        print(f"auth mode: browser session cookie ({len(cookie)} chars, "
              f"{cookie.count('=')} cookie(s))")
        return CookieAuth(cookie)
    print("auth mode: OAuth2 token (paid-subscriber path)")
    creds = dict(
        username=os.environ.get("EOG_USERNAME") or input("EOG username: ").strip(),
        password=os.environ.get("EOG_PASSWORD") or getpass.getpass("EOG password: "),
        client_id=os.environ.get("EOG_CLIENT_ID") or input("EOG client_id: ").strip(),
        client_secret=os.environ.get("EOG_CLIENT_SECRET") or getpass.getpass("EOG client_secret: "),
        grant_type="password",
    )
    auth = TokenAuth(creds)
    auth.warmup()                            # fail fast on bad creds
    print("auth OK -- token acquired")
    return auth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="permian_sites_full.csv")
    ap.add_argument("--id-col", default="flare_id")
    ap.add_argument("--out", default="vnf_sites")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--retries", type=int, default=5)
    ap.add_argument("--min-bytes", type=int, default=50)
    ap.add_argument("--delay", type=float, default=0.1)
    ap.add_argument("--cookie-file", default=None,
                    help="path to a text file containing your Cookie header")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ids = read_ids(args.catalog, args.id_col)
    print(f"{len(ids)} site ids read from {args.catalog}")

    if args.dry_run:
        for i in ids[:10]:
            print(build_url(i))
        print(f"... ({len(ids)} total)")
        return

    if "PASTE" in BASE_URL:
        sys.exit("Set BASE_URL first (the folder your site_20227 file came from).")

    auth = make_auth(args.cookie_file)
    os.makedirs(args.out, exist_ok=True)
    session = requests.Session()
    stop = threading.Event()

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {}
        for i in ids:
            futs[ex.submit(download_one, session, auth, i, args.out,
                           args.timeout, args.retries, args.min_bytes, stop)] = i
            time.sleep(args.delay)
        for n, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            if n % 50 == 0 or n == len(ids):
                have = sum(1 for r in results if r[1] in ("ok", "skip"))
                print(f"  {n}/{len(ids)} processed | {have} present on disk")

    with open(os.path.join(args.out, "_manifest.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["flare_id", "status", "bytes", "url_if_problem"])
        w.writerows(sorted(results))

    counts = Counter(r[1] for r in results)
    print("summary:", dict(counts))
    problems = [r for r in results if r[1] in ("fail", "404", "bad_content")]
    if problems:
        print(f"{len(problems)} problem ids in {args.out}/_manifest.csv -- re-run to retry just those.")
    if any(r[1] in ("auth_error", "auth_stopped") for r in results):
        print("\nAUTH STOPPED: the session cookie expired mid-run. Re-copy a fresh "
              "cookie into your cookie file and re-run the SAME command -- resume "
              "skips everything already downloaded.")


if __name__ == "__main__":
    main()
