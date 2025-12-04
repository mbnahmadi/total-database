import mercantile
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from PIL import Image

tif_path = "temperature_3857_cog.tif"  # فایل COG ساخته شده
tile_size = 256  # سایز تایل استاندارد

# ===== تابع محاسبه bounds تایل در CRS فایل =====
def tile_bounds_in_dataset_crs(x, y, z, dst_crs="EPSG:3857"):
    b = mercantile.bounds(x, y, z)  # WGS84
    transformer = Transformer.from_crs("EPSG:4326", dst_crs, always_xy=True)
    left, bottom = transformer.transform(b.west, b.south)
    right, top = transformer.transform(b.east, b.north)
    return (left, bottom, right, top)

# ===== تابع اصلی گرفتن tile =====
def get_tile(x, y, z):
    bounds = tile_bounds_in_dataset_crs(x, y, z, dst_crs="EPSG:3857")
    with rasterio.open(tif_path) as src:
        # WarpedVRT با resampling bilinear
        with WarpedVRT(src, crs="EPSG:3857", resampling=Resampling.bilinear) as vrt:
            # محاسبه window مطابق bounds
            window = vrt.window(*bounds)

            if window.width <= 0 or window.height <= 0:
                raise ValueError("Computed window is empty: " + str(window))

            bands = vrt.count
            # read داده‌ها و resample به tile_size
            data = vrt.read(window=window, out_shape=(bands, tile_size, tile_size))

            # تبدیل به (H, W, bands)
            img = np.transpose(data, (1, 2, 0))

            # اگر فقط یک باند (مثل دما) داریم، normalize و RGBA بسازیم
            if bands == 1:
                arr = img[:, :, 0]
                arr = np.nan_to_num(arr, nan=np.nanmin(arr))
                vmin, vmax = np.nanmin(arr), np.nanmax(arr)
                if vmax == vmin:
                    vmax = vmin + 1.0
                norm = (arr - vmin) / (vmax - vmin)
                # انتخاب colormap (turbo یا coolwarm)
                from matplotlib import cm
                cmap = cm.get_cmap("turbo")
                rgba = cmap(norm)
                rgba_uint8 = (rgba * 255).astype(np.uint8)
                pil = Image.fromarray(rgba_uint8, mode="RGBA")
            else:
                # اگر چند باند هست، assume uint8 RGBA یا RGB
                if data.dtype == np.uint8 and bands in (3,4):
                    mode = "RGBA" if bands==4 else "RGB"
                    pil = Image.fromarray(img, mode=mode)
                else:
                    # fallback: نرمالایز 3 باند اول
                    arr = img[:, :, :3]
                    norm_rgb = np.zeros_like(arr, dtype=np.uint8)
                    for i in range(3):
                        ch = arr[:, :, i]
                        ch = np.nan_to_num(ch, nan=np.nanmin(ch))
                        vmin, vmax = ch.min(), ch.max()
                        if vmax==vmin:
                            vmax = vmin + 1.0
                        norm_rgb[:, :, i] = ((ch - vmin)/(vmax-vmin)*255).astype(np.uint8)
                    rgba_uint8 = np.dstack([norm_rgb, np.full((tile_size, tile_size), 255, dtype=np.uint8)])
                    pil = Image.fromarray(rgba_uint8, mode="RGBA")

            return pil

# ===== تست با یک tile در محدوده Persian Gulf =====
if __name__ == "__main__":
    # مثال: زوم و x,y مربوط به خلیج فارس
    z, x, y = 5, 20, 12
    tile_img = get_tile(x, y, z)
    tile_img.save("tile_test_ready.png")
    print("✅ Tile ساخته شد: tile_test_ready.png")
