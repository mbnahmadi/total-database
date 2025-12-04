import xarray as xr
import rioxarray  # noqa
from rasterio.enums import Resampling

# # مسیر فایل NetCDF
# input_file = "D:\\project\\TotalDB\\TOTALDB_CYCLES\\wind\\PersianGulf\\2025101412\\merged_nc_file.nc"

# # باز کردن فایل
# ds = xr.open_dataset(input_file)

# # انتخاب اولین timestep
# da = ds["T2"].isel(time=0)

# # تبدیل دما از Kelvin به Celsius
# da_c = da - 273.15

# # ✅ اگر مختصات توی فایل latitude / longitude یا lat / lon هست:
# da_c = da_c.rename({
#     "lat": "y",
#     "lon": "x"
# }) 

# # ✅ اعلام ابعاد مکانی به rioxarray
# da_c.rio.set_spatial_dims(x_dim="x", y_dim="y", inplace=True)

# # ✅ نوشتن CRS
# da_c.rio.write_crs("EPSG:4326", inplace=True)

# # ✅ ذخیره به GeoTIFF
# da_c.rio.to_raster("temperature_4326.tif")

# print("✅ مرحله اول: GeoTIFF ساخته شد -> temperature_4326.tif")

import rioxarray
import matplotlib.pyplot as plt
import numpy as np
import rasterio

tif_in = "temperature_3857_cog.tif"
tif_out = "temperature_rgba2.tif"

# خواندن فایل
da = rioxarray.open_rasterio(tif_in)

# به numpy تبدیل کن
data = da.squeeze().values

# حداقل و حداکثر دما برای نرمال‌سازی
vmin, vmax = np.nanmin(data), np.nanmax(data)
norm = (data - vmin) / (vmax - vmin)

# انتخاب colormap (مثلاً "coolwarm" یا "turbo")
cmap = plt.get_cmap("turbo")
rgba = cmap(norm)

# rgba آرایه‌ای با shape=(y,x,4) هست، باید به uint8 تبدیلش کنیم
rgba_uint8 = (rgba * 255).astype(np.uint8)

# ذخیره RGBA GeoTIFF
with rasterio.open(
    tif_out,
    "w",
    driver="GTiff",
    height=rgba_uint8.shape[0],
    width=rgba_uint8.shape[1],
    count=4,
    dtype="uint8",
    crs=da.rio.crs,
    transform=da.rio.transform(),
) as dst:
    for i in range(4):
        dst.write(rgba_uint8[:, :, i], i + 1)

print("✅ TIFF رنگی ساخته شد ->", tif_out)