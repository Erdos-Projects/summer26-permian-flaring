# VIIRS Nightfire (VNF) Extraction Pipeline

This directory contains the Python automation logic used to ingest, filter, and normalize thermal anomaly data from the Earth Observation Group (EOG) VIIRS VNF database.

## Overview
This pipeline retrieves daily global thermal data and filters it for the Permian Basin region. It supports the full VIIRS satellite constellation (`npp`, `j01`, `j02`). 

## Technical Architecture
* **Zero-Footprint Processing:** To preserve SSD longevity, the script utilizes `io.BytesIO` to stream data directly into system RAM. No temporary files are written to the disk during the download and parsing phase.
* **Authentication:** The script mimics a Safari browser session via `cf_clearance` tokens injected through environment variables.
* **State Management:** The script maintains `processed_logs.txt` to prevent duplicate downloads and to cache `404` errors (e.g., when a satellite was not yet operational), allowing for safe interruption and resumption.

## Prerequisites
1.  **Environment:** Ensure your Conda environment includes `pandas`, `requests`, and `python-dotenv`.
2.  **Configuration:** You **must** have a `.env` file in the project root containing your valid `EOG_COOKIE`.
3.  **Security:** This directory and its contents are monitored by `.gitignore`. **Do not** commit your `.env` file or raw data files to the repository.

## Usage
Run the script via your terminal:
```bash
python download_viirs_vnf.py

You will be prompted to enter the target year and month. Entering only the year will trigger a download for the full 12-month period.