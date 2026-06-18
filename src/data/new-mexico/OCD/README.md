# OCD Regulatory Data Processing

This directory contains the processing scripts responsible for parsing, cleaning, and filtering the official records from the New Mexico Oil Conservation Division (OCD).

## 📄 Contents
*   **`build_regulatory_timeseries.py`**: Extracts raw state waste ledgers, separates production product types, maps them through infrastructure crosswalks, and formats them for the dual-axis visualization tools.

---

## 💡 Core Analytical Hypotheses
1. **Infrastructure Elasticity**: Midstream gathering assets (compressor stations, processing plants) display different waste profiles than upstream asset points (well pads). This directory treats `Structure_ID` as a polymorphic key to isolate and evaluate both categories.
2. **Product Kind Mismatches**: Oil production ('O') and gas flaring/venting waste ('G') are inherently coupled during extraction. Tracking the relationship between barrels of oil produced (BBL) and thousands of cubic feet of gas wasted (MCF) exposes operational efficiency limits across individual sites.

---

## 🛠️ Code Logic & Architecture

### 1. Relational Key Standardization
State ledgers often mix types or include padding inside identifier columns (e.g., treating API numbers as integers in one file and hyphenated strings in another), which causes silent merge drops.
* **Type Hardening**: The script explicitly casts `Structure_ID`, `API_Number`, and `Facility_ID` columns into clean, whitespace-stripped string data types before initiating relational table joins.
* **Strict Inner Mapping**: Using an outer join would pull in thousands of administrative "ghost wells" (abandoned, shut-in, or dry holes). The script enforces strict inner joins against the non-zero upstream waste tables, instantly filtering the mapping array down to active emitters.

### 2. Stream-Specific Volume Isolation
Because oil and gas volumes use completely different tracking metrics, summing them together creates corrupt indicators. The pipeline filters out gas volumes ('G') for site-level gas infrastructure monitoring, while compiling oil volumes ('O') into a separate vector to evaluate base commodity throughput.