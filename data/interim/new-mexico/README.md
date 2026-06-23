# Interim Data Dictionary

This document outlines the schemas, granularity, and physical interpretations of the parsed CSV datasets extracted from the raw New Mexico Oil Conservation Division (OCD) administrative registries.

---

## 1. Production Data
**File:** `nm_wcproduction_filtered.csv`
**Source:** `wcproduction.xml`
**Granularity:** Well-Month (`API_Number` + `Year` + `Month`)
**Description:** Contains the audited, physical volumes of hydrocarbons extracted from the ground. Filtered exclusively for the Delaware Basin (Lea and Eddy counties) and hydrocarbon streams (Oil and Gas).

| Column | Type | Description |
| :--- | :--- | :--- |
| `API_Number` | String | Standard 10-digit well identifier (e.g., 30-025-XXXXX). |
| `Operator_ID` | String | The OGRID (company identifier) of the producer. |
| `Year` | Integer | Production year. |
| `Month` | Integer | Production month. |
| `Product_Kind` | Category | 'G' for Natural Gas, 'O' for Crude Oil. |
| `Volume` | Float | The extracted volume (MCF for Gas, Bbls for Oil). |

---

## 2. Gas Sales (Delivery) Data
**File:** `nm_gas_sold.csv`
**Source:** `podvolume.xml`
**Granularity:** Operator-Month (`Operator_ID` + `Year` + `Month`)
**Description:** Represents the volume of gas successfully pushed into commercial midstream pipelines (Disposition Code 'D'). Crucial for calculating the Sales-to-Production ratio and determining system shrinkage.

| Column | Type | Description |
| :--- | :--- | :--- |
| `Operator_ID` | String | The OGRID of the selling company. |
| `Year` | Integer | Sales year. |
| `Month` | Integer | Sales month. |
| `Gas_Sold_MCF` | Float | Total audited volume of gas sold to market. |

---

## 3. Modern Waste & Flaring Data (2021–Present)
**File:** `nm_upstream_waste_nonzero.csv`
**Source:** `upstreamnaturalgaswaste.xml`
**Granularity:** Operator-Event/Month
**Description:** The strict environmental logs mandated by the 2021 Waste Rule. Tracks gas that was physically combusted (flared) or released (vented) into the atmosphere. Zero-volume rows are explicitly dropped to conserve memory.

| Column | Type | Description |
| :--- | :--- | :--- |
| `Year` | Integer | Reporting year. |
| `Month` | Integer | Reporting month. |
| `OGRID` | String | Operator ID (Mapped to `Operator_ID` downstream). |
| `Structure_Type` | Category | Context of the waste event (e.g., Facility vs. Well). |
| `Structure_ID` | String | The specific flare stack or lease ID. |
| `Waste_Type` | Category | E.g., Flared, Vented. |
| `Reporting_Category` | Category | The regulatory reason for the waste (e.g., Equipment Failure, Midstream Bottleneck). |
| `Volume_MCF` | Float | The total wasted volume. |
| `Method` | String | How the volume was determined (Metered vs. Estimated). |

---

## 4. Modern Beneficial Use Data (2021–Present)
**File:** `nm_upstream_beneficial_use_nonzero.csv`
**Source:** `upstreamnaturalgaswastebeneficialuse.xml`
**Granularity:** Operator-Event/Month
**Description:** Tracks un-sold gas that was intercepted and utilized by the operator for lease operations (e.g., powering compressor engines or gas-lift mechanics).

| Column | Type | Description |
| :--- | :--- | :--- |
| `reporting_period_year`| Integer | Reporting year. |
| `reporting_period_month`| Integer| Reporting month. |
| `ogrid` | String | Operator ID. |
| `structure_type` | Category | Context of the use. |
| `structure_id` | String | Identifier of the specific engine or facility. |
| `use_type` | Category | Standardized code for how the gas was utilized. |
| `use_type_other` | String | Free-text field for non-standard uses. |
| `volume` | Float | The volume of gas burned for operational power (MCF). |
| `saved` | Datetime | Administrative timestamp of the log entry. |

---

## 5. Wellhead Spatial Registry
**File:** `nm_wells_spatial.csv`
**Source:** `New_Mexico_OCD_Oil_and_Gas_Wells.csv`
**Granularity:** Well (`API_Number`)
**Description:** The master crosswalk linking standard administrative well IDs to physical earth coordinates. Essential for generating spatial buffers to intersect with VIIRS Nightfire thermal satellite anomalies.

| Column | Type | Description |
| :--- | :--- | :--- |
| `API_Number` | String | Standard 10-digit well identifier. |
| `Operator_ID` | String | The OGRID of the company that drilled/owns the well. |
| `Well_Type` | Category | Primary target fluid (Gas vs. Oil). |
| `Well_Status` | Category | E.g., Active, Plugged, New. |
| `County_Code` | String | FIPS code (15 = Eddy, 25 = Lea). |
| `Latitude` | Float | NAD83 Y-coordinate. |
| `Longitude` | Float | NAD83 X-coordinate. |

---

## 6. Surface Infrastructure Spatial Registry
**File:** `nm_facilities.csv`
**Source:** `facility.xml`
**Granularity:** Facility (`id`)
**Description:** Maps the physical locations of midstream hardware (compressor stations, gathering satellites, below-grade tanks). Used to identify spatial chokepoints in the pipeline network.

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | String | Unique facility identifier. |
| `name` | String | Operational name of the site. |
| `type_code` | Category | E.g., MGS (Metering/Gathering Satellite), BGT. |
| `type` | String | Full text description of the facility type. |
| `status_code` | Category | Administrative status. |
| `status` | String | Full text description of the status. |
| `ogrid` | String | Operator ID. |
| `ogrid_name` | String | Full company name. |
| `county_code` | String | FIPS code. |
| `latitude` | Float | NAD83 Y-coordinate. |
| `longitude` | Float | NAD83 X-coordinate. |
| `effective_date` | Datetime| When the facility came online. |

---

## 7. Legacy Mapping Dictionary
**File:** `nm_pod_to_api_mapping.csv`
**Source:** Internally generated crosswalk
**Granularity:** POD-API Link
**Description:** Used exclusively to bridge the gap in pre-2021 data by mapping communal Point of Delivery (POD) meters back to the specific wellbores that feed them.
