import numpy as np
import geopandas as gpd
import rioxarray as rxr
import xarray as xr


# Read in the data
in_raster = rxr.open_rasterio("data/CLCD_v01_2010_albert.tif", chunks='auto')
in_vector = gpd.read_file("data/China_shp/China_City_2020_Del_Albert_Project.shp")

beijing_shp = in_vector[in_vector['ENG_NAME'] == 'Beijing']
beijing_raster = in_raster.rio.clip(beijing_shp.geometry)








