# Raw Data Directory

The raw data files are too large to host on GitHub. Follow the instructions below to download various raw datasets required for the project.

## New-Mexico OCD Data

The Oil Conservation Division (OCD) is a regulatory agency under the New Mexico Energy, Minerals and Natural Resources Department (EMNRD). It oversees oil, gas, and geothermal operations, focusing on issuing drilling permits, gathering production data, managing environmental compliance, and ensuring the proper plugging and restoration of abandoned wells. The OCD Hub can be accessed at https://ocd-hub-nm-emnrd.hub.arcgis.com.

1. Connect to the NM OCD FTP Server. See [instructions](https://www.emnrd.nm.gov/ocd/ocd-data/ftp-server/) on how to connect to the FTP Server.
2. Download the following files:
    * `wcproduction.zip`
    * `upstreamnaturalgaswaste.zip`
    * `podvolume.zip` 
    * `podwc.zip`
    * `Facility.zip`
    * `upstreamnaturalgaswastebeneficialuse.zip`
3. Extract the `.xml` files and place them exactly in the directory (`data/raw/new-mexico/OCD/`).
4. Run the scripts in `src/data/new-mexico/OCD/` to generate the interim datasets.

The data layout of all the files in the FTP server can be accessed [here](https://www.emnrd.nm.gov/ocd/wp-content/uploads/sites/6/OCD-Interface-v1.1-Data-Dictionary-Protected.xlsx). 

Download the New Mexico Oil and Gas Wells details [here](https://ocd-hub-nm-emnrd.hub.arcgis.com/datasets/387f397ebf164c7aa6a752aac7d22b17_0/about).
