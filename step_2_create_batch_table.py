import os
import pandas as pd
from glob import glob


# Get the list of the clipped raster files
clipped_rasters = glob("data/clipped_rasters/*.tif")
clipped_rasters = [[
    os.path.abspath(raster),    # Absolute path to the raster
    'x',                # Cell size: The integer value corresponding to the cell size (in meters).      
    '999',              # Background value: The designated background value. 
    'x',                # Number of rows: The number of rows in the input image
    'x',                # Number of columns: The number of columns in the input image.
    1,                  # Band number: The band number to interpret in the input image, which by default is #1 but can vary for some of the input data formats.
    'x',                # Nodata value: The integer value corresponding to the nodata value.
    'IDF_GeoTIFF'       # Input data format: The input data format (e.g., IDF_GeoTIFF, IDF_ASCII, IDF_8BIT, etc.). Note, GeoTIFFs does not require cell size, number of rows and columns, and nodata value are not needed; an "x" is used in place of the argument.
    ] for raster in clipped_rasters]


# Create a DataFrame from the list
clipped_df = pd.DataFrame(clipped_rasters)
clipped_df.to_csv("data/clipped_rasters.csv", index=False, header=False)

