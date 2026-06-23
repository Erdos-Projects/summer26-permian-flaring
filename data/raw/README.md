# Raw Data Directory

The raw data files are too large to host on GitHub. Follow the instructions below to download various raw datasets required for the project.

## New-Mexico OCD Data

The Oil Conservation Division (OCD) is a regulatory agency under the New Mexico Energy, Minerals and Natural Resources Department (EMNRD). It oversees oil, gas, and geothermal operations, focusing on issuing drilling permits, gathering production data, managing environmental compliance, and ensuring the proper plugging and restoration of abandoned wells. The OCD Hub can be accessed at https://ocd-hub-nm-emnrd.hub.arcgis.com.

1. Connect to the NM OCD FTP Server. See [instructions](https://www.emnrd.nm.gov/ocd/ocd-data/ftp-server/) on how to connect to the FTP Server.
2. Download `wcproduction.xml` and `upstreamnaturalgaswaste.xml` from `/Public/OCD/OCD Interface v1.1/volumes/wcproduction/` and `/Public/OCD/OCD Interface v1.1/other/upstreamnaturalgaswaste/` folders respectively.
3. Place them exactly in the directory (`data/raw/new-mexico/OCD/`).
4. Run the scripts in `src/data/new-mexico/OCD/` to generate the interim datasets.

The upstream natural gas waste data layout can be accessed [here](https://www.emnrd.nm.gov/ocd/wp-content/uploads/sites/6/User-Guide-for-the-C-115B-Upstream-Natural-Gas-Waste-Report-1.pdf).

The column details of the files `wcproduction.xml` are given below:

|Column Name| Data Type|
|---|---|
|api_st_cde                | sqltypes:smallint|
|api_cnty_cde              | sqltypes:smallint|
|api_well_idn              | sqltypes:int|
|pool_idn                  | sqltypes:int|
|prodn_mth                 | sqltypes:smallint|
|prodn_yr                  | sqltypes:int|
|ogrid_cde                 | sqltypes:int|
|prd_knd_cde               | sqltypes:char|
|eff_dte                   | sqltypes:datetime|
|amend_ind                 | sqltypes:char|
|c115_wc_stat_cde          | sqltypes:char|
|prod_amt                  | sqltypes:int|
|prodn_day_num             | sqltypes:smallint|
|mod_dte                   | sqltypes:datetime|


The column details of the files `upstreamnaturalgaswaste.xml` are given below:

COLUMN NAME               | DATA TYPE
---|---
reporting_period_year     | sqltypes:int
reporting_period_month    | sqltypes:int
ogrid                     | sqltypes:int
structure_type            | sqltypes:char
structure_id              | sqltypes:varchar
waste_type                | sqltypes:char
reporting_category        | sqltypes:varchar
volume                    | sqltypes:int
determination_method      | sqltypes:varchar
saved                     | sqltypes:datetime