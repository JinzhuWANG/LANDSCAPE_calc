import numpy as np
import geopandas as gpd
import rioxarray as rxr
import xarray as xr

from joblib import Parallel, delayed
from tqdm.auto import tqdm

# Read in the data
in_raster = rxr.open_rasterio("data/CLCD_v01_2010_albert.tif", chunks='auto')
in_vector = gpd.read_file("data/China_shp/China_City_2020_Del_Albert_Project.shp")

city_names = in_vector['ENG_NAME'].values



# Function to clip the raster
def clip_raster(raster, name):
    # Get the city shp
    vector = in_vector[in_vector['ENG_NAME'] == name]
    # Clip the raster with the city shp
    clipped_raster = raster.rio.clip(vector.geometry)
    # Save clipped raster
    clipped_raster.rio.to_raster(f"data/clipped_rasters/{name}.tif", compress='LZW')


# Define the parallel object
para_obj = Parallel(n_jobs=3, return_as='generator')
tasks = (delayed(clip_raster)(in_raster, name) for name in city_names)



# Run the parallel process
with tqdm(total=len(in_vector)) as pbar:
    for _ in para_obj(tasks):
        pbar.update(1)








