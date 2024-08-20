import os
import rasterio
from rasterio import features
from rasterio.mask import mask
import geopandas as gpd
import pandas as pd
import math
from tqdm import tqdm
from rasterio.windows import Window
from shapely.geometry import shape

# Input and output file paths
data_path = 'data'
infile = f'{data_path}/CLCD_v01_2010_albert.tif'
outfile = f'{data_path}/CLCD_v01_2010_albert_china_Frac_AI.shp'
shapefile = f'{data_path}/China_shp/China_City_2020_Del_Albert_Project.shp'  # Input shapefile for administrative boundaries
chunk_size = 1024  # Size for processing chunks

# Functions for calculating different indices
def calculate_frac(perimeter, area):
    if area <= 0 or perimeter <= 0:
        return None
    return (2 * math.log(0.25 * perimeter)) / math.log(area)

def calculate_aggregation_index(raster_patch):
    """
    Calculate the Aggregation Index (AI) for a raster patch.
    AI = (number of like adjacencies / maximum number of like adjacencies) * 100
    """
    total_cells = raster_patch.size
    if total_cells <= 1:
        return None  # Return None for patches with 0 or 1 cell

    max_adj = 2 * total_cells * (total_cells - 1)  # The maximum number of like adjacencies
    like_adj = 0

    # Calculate the number of like adjacencies
    for i in range(raster_patch.shape[0]):
        for j in range(raster_patch.shape[1]):
            if i > 0 and raster_patch[i, j] == raster_patch[i-1, j]:  # Up
                like_adj += 1
            if j > 0 and raster_patch[i, j] == raster_patch[i, j-1]:  # Left
                like_adj += 1

    if max_adj == 0:
        return None  # This should not happen, but just in case
    
    ai = (like_adj / max_adj) * 100  # AI is expressed as a percentage
    return ai

def process_admin_unit(admin, NLUM_ID_raster, NLUM_transform):
    mask = features.geometry_mask([admin.geometry], transform=NLUM_transform, invert=True, out_shape=NLUM_ID_raster.shape)
    results = [{'properties': {'NLUM_ID': v, 'admin_id': admin['ID']}, 'geometry': s}
               for s, v in features.shapes(NLUM_ID_raster, mask=mask, transform=NLUM_transform) if v == 1]
    return results

def calculate_indices(result):
    geometry = shape(result['geometry'])  # Convert the geometry dict to a shapely object
    raster_patch = result['raster_patch']  # Extract the raster patch

    perimeter = geometry.length
    area = geometry.area
    ai = calculate_aggregation_index(raster_patch)  # Calculate AI

    indices = {
        'area': area,
        'perimeter': perimeter,
        'frac': calculate_frac(perimeter, area),
    }
    
    if ai is not None:
        indices['aggregation_index'] = ai
    else:
        indices['aggregation_index'] = None  # or use a default value like 0 or -1

    return indices

def extract_raster_patch(raster, geometry, transform):
    """Extract the raster values for the given geometry."""
    # Create a mask for the geometry
    out_image, out_transform = mask(raster, [geometry], crop=True)
    return out_image[0]  # Return the masked raster data

def process_raster_file(infile, chunk_size, admin_geometries):
    with rasterio.open(infile) as rst:
        width = rst.width
        height = rst.height
        NLUM_transform = rst.transform
        NLUM_crs = rst.crs

        all_results = []
        indices_results = []

        for i in tqdm(range(0, height, chunk_size), desc=f'Processing {os.path.basename(infile)}', unit='block'):
            for j in range(0, width, chunk_size):
                window = Window(j, i, min(chunk_size, width - j), min(chunk_size, height - i))
                transform = rst.window_transform(window)
                NLUM_ID_raster = rst.read(1, window=window, masked=True)

                for admin in admin_geometries:
                    results = process_admin_unit(admin, NLUM_ID_raster, transform)
                    all_results.extend(results)

                    for result in results:
                        raster_patch = extract_raster_patch(rst, shape(result['geometry']), transform)
                        result['raster_patch'] = raster_patch  # Store raster patch in the result
                        indices = calculate_indices(result)  # Pass the entire result dictionary
                        indices['geometry'] = shape(result['geometry'])  # Convert to shapely geometry
                        indices['admin_id'] = result['properties']['admin_id']
                        indices_results.append(indices)

        # Convert all collected features to GeoDataFrame
        gdfp = gpd.GeoDataFrame.from_features(all_results, crs=NLUM_crs)
        
        # Create indices_gdf with explicit geometry column
        indices_gdf = gpd.GeoDataFrame(indices_results, geometry='geometry', crs=NLUM_crs)

        # Debug information
        print(f"Number of indices results: {len(indices_results)}")
        print("Keys in the first result:", indices_results[0].keys() if indices_results else "No results")
        print("Type of geometry in the first result:", type(indices_results[0]['geometry']) if indices_results and 'geometry' in indices_results[0] else "No geometry")

        return gdfp, indices_gdf

if __name__ == '__main__':
    # Read the shapefile for administrative boundaries
    admin_gdf = gpd.read_file(shapefile)
    admin_geometries = [admin for _, admin in admin_gdf.iterrows()]

    # Process the raster file
    gdfp, indices_gdf = process_raster_file(infile, chunk_size, admin_geometries)

    # Calculate average indices for each administrative unit
    admin_results = admin_gdf.copy()
    admin_results['avg_frac'] = admin_results['ID'].apply(lambda x: indices_gdf[indices_gdf['admin_id'] == x]['frac'].dropna().mean())
    admin_results['avg_ai'] = admin_results['ID'].apply(lambda x: indices_gdf[indices_gdf['admin_id'] == x]['aggregation_index'].dropna().mean())

    # Export results as a shapefile
    admin_results.to_file(outfile, driver='ESRI Shapefile')
    
    