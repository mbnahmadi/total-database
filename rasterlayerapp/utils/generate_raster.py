import os
import psycopg2
import pandas as pd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import get_cmap

# --- تنظیمات ---
DB_CONFIG = {
    "dbname": "totaldb",
    "user": "postgres",
    "password": "123456789",
    "host": "localhost",
    "port": 5432
}

MIN_LAT, MAX_LAT = 22.94, 30.54
MIN_LON, MAX_LON = 46.25, 58.25
RES = 0.01
OUTPUT_PATH = "temperature_color_transparent2.tif"

# --- واکشی داده‌ها ---
def fetch_data():
    conn = psycopg2.connect(**DB_CONFIG)
    query = """
        SELECT 
            ST_X(s.location::geometry) AS lon,
            ST_Y(s.location::geometry) AS lat,
            f.temperature,
            f.forecast_time
        FROM windforecastapp_windforecastmodel f
        JOIN windforecastapp_windstationmodel s ON f.station_id = s.id
        WHERE f.forecast_time = (
            SELECT MIN(forecast_time) FROM windforecastapp_windforecastmodel
        )
        AND ST_Y(s.location::geometry) BETWEEN %s AND %s
        AND ST_X(s.location::geometry) BETWEEN %s AND %s
    """
    df = pd.read_sql(query, conn, params=(MIN_LAT, MAX_LAT, MIN_LON, MAX_LON))
    conn.close()
    df["temperature"] = df["temperature"] - 273.15
    return df

# --- ایجاد raster شفاف ---
def create_raster_transparent(df, output_path=OUTPUT_PATH):
    lon_grid = np.arange(MIN_LON, MAX_LON, RES)
    lat_grid = np.arange(MAX_LAT, MIN_LAT, -RES)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

    points = np.array(list(zip(df["lon"], df["lat"])))
    values = df["temperature"].values
    grid = griddata(points, values, (lon_mesh, lat_mesh), method="linear")

    # colormap با آلفا (شفافیت)
    cmap = get_cmap('viridis')
    norm = Normalize(vmin=np.nanmin(grid), vmax=np.nanmax(grid))
    rgba = cmap(norm(grid))
    
    # تنظیم شفافیت: جاهایی که داده NaN هست کاملاً شفاف
    rgba[:,:,3] = np.where(np.isnan(grid), 0, 0.6)  # 0.6 یعنی کمی شفاف، می‌تونی 0.4-0.7 تنظیم کنی

    transform = from_origin(MIN_LON, MAX_LAT, RES, RES)

    with rasterio.open(
        output_path,
        "w",
        driver="GTiff",
        height=rgba.shape[0],
        width=rgba.shape[1],
        count=4,
        dtype='uint8',
        crs="EPSG:4326",
        transform=transform
    ) as dst:
        for i in range(4):
            dst.write((rgba[:,:,i]*255).astype('uint8'), i+1)
        dst.update_tags(
            variable="temperature",
            units="°C",
            forecast_time=str(df["forecast_time"].iloc[0])
        )

    print(f"✅ GeoTIFF شفاف ذخیره شد: {output_path}")

# --- اجرا ---
if __name__ == "__main__":
    df = fetch_data()
    print(f"📊 {len(df)} رکورد بازیابی شد")
    create_raster_transparent(df)
