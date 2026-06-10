# Raw Data Directory

The raw data files are too large to host on GitHub. To replicate this project:
1. Connect to the NM OCD FTP Server.
2. Download `wcproduction.xml` and `upstreamnaturalgaswaste.xml`.
3. Place them exactly in this directory (`data/raw/new-mexico/`).
4. Run `python src/data/parse_production.py` to generate the interim datasets.
