from django.shortcuts import render
import rasterio
from rasterio.windows import Window
from django.http import HttpResponse
from PIL import Image
import numpy as np
import io
import math

import matplotlib.pyplot as plt

# views.py
import io
from datetime import datetime
import xarray as xr

# مسیر فایل NetCDF
NC_FILE = "D:\\project\\TotalDB\\TOTALDB_CYCLES\\wind\\PersianGulf\\2025101412\\merged_nc_file.nc"

ds = xr.open_dataset(NC_FILE)

TILE_SIZE = 256
ALPHA = 200  # شفافیت
TEMP_MIN = 20.0  # سانتی‌گراد
TEMP_MAX = 35.0  # سانتی‌گراد

LAT_MIN = float(ds['lat'].min())
LAT_MAX = float(ds['lat'].max())
LON_MIN = float(ds['lon'].min())
LON_MAX = float(ds['lon'].max())

# تبدیل tile x,y,z به bounding box
def lonlat_bounds_from_tile(x, y, z):
    n = 2.0 ** z
    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0
    lat_min = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * (y + 1) / n))))
    lat_max = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * y / n))))
    return lon_min, lon_max, lat_min, lat_max

# View اصلی
def tile_temperature(request, z, x, y):
    z, x, y = int(z), int(x), int(y)
    lon_min_tile, lon_max_tile, lat_min_tile, lat_max_tile = lonlat_bounds_from_tile(x, y, z)

    # خارج از محدوده داده → transparent
    if lon_max_tile < LON_MIN or lon_min_tile > LON_MAX or \
       lat_max_tile < LAT_MIN or lat_min_tile > LAT_MAX:
        img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (0,0,0,0))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return HttpResponse(buffer.getvalue(), content_type='image/png')

    # محدود کردن tile به محدوده داده‌ها
    lon_min_tile = max(lon_min_tile, LON_MIN)
    lon_max_tile = min(lon_max_tile, LON_MAX)
    lat_min_tile = max(lat_min_tile, LAT_MIN)
    lat_max_tile = min(lat_max_tile, LAT_MAX)

    # انتخاب snapshot (اولین زمان)
    temp_data = ds['T2'].isel(time=0).values - 273.15  # سانتی‌گراد
    lat_vals = ds['lat'].values
    lon_vals = ds['lon'].values

    # انتخاب subset
    lat_mask = (lat_vals >= lat_min_tile) & (lat_vals <= lat_max_tile)
    lon_mask = (lon_vals >= lon_min_tile) & (lon_vals <= lon_max_tile)
    subset = temp_data[np.ix_(lat_mask, lon_mask)]

    # resize ساده به TILE_SIZE × TILE_SIZE
    img_arr = Image.fromarray(subset)
    img_arr = img_arr.resize((TILE_SIZE, TILE_SIZE), resample=Image.BILINEAR)

    # نرمال‌سازی و RGBA ساده (red-blue colormap)
    arr = np.array(img_arr)
    arr = np.clip(arr, TEMP_MIN, TEMP_MAX)
    norm = ((arr - TEMP_MIN) / (TEMP_MAX - TEMP_MIN) * 255).astype(np.uint8)

    rgba = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
    rgba[...,0] = norm          # R
    rgba[...,2] = 255 - norm    # B
    rgba[...,3] = ALPHA         # alpha

    final_img = Image.fromarray(rgba, mode='RGBA')
    buffer = io.BytesIO()
    final_img.save(buffer, format='PNG')
    return HttpResponse(buffer.getvalue(), content_type='image/png')


# Create your views here.
def map_view(request):
    return render(request, "map.html")