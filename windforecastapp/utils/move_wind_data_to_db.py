import os
import gc
import logging
import xarray as xr
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime
from django.contrib.gis.geos import Point
from windforecastapp.models import WindStationModel, WindForecastModel
from postgres_copy import CopyMapping
from scipy.spatial import cKDTree

# ---------- Logging Setup ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("weather_import.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def move_to_db(file_path):
    logger.info("start processing file: %s", file_path)

    if not os.path.isfile(file_path):
        logger.error("file not found: %s", file_path)
        return

    # باز کردن فایل NetCDF
    try:
        ds = xr.open_dataset(file_path, engine='netcdf4')
    except Exception as e:
        logger.exception("error in opening netcdf file: %s", e)
        return

    # گرفتن مختصات
    try:
        lat = ds['lat'].values  # shape: (Y, X)
        lon = ds['lon'].values  # shape: (Y, X)
        y, x = lat.shape
        logger.info("network dimensions: %d × %d", y, x)
    except Exception as e:
        logger.exception("error in extracting coordinates: %s", e)
        return

    # ایجاد ایستگاه‌ها فقط اگر جدول خالی است
    try:
        if not WindStationModel.objects.exists():
            logger.info("no station found, start creating stations...")

            stations_df = pd.DataFrame({
                'latitude': lat.ravel(),
                'longitude': lon.ravel(),
                'name': [f"Station_{i}" for i in range(y * x)]
            })

            stations_io = StringIO()
            stations_df.to_csv(stations_io, index=False)
            stations_io.seek(0)

            stations_mapping = CopyMapping(
                WindStationModel,
                stations_io,
                dict(latitude='latitude', longitude='longitude', name='name')
            )
            stations_mapping.save()
            logger.info("stations created successfully.")
    except Exception as e:
        logger.exception("error in creating or inserting stations: %s", e)
        return

    # حذف پیش‌بینی‌های قبلی
    try:
        WindForecastModel.objects.all().delete()
        logger.info("all previous forecast data deleted.")
    except Exception as e:
        logger.exception("error in deleting previous forecast data: %s", e)
        return

    # گرفتن ایستگاه‌ها و ساخت دیکشنری
    try:
        stations = WindStationModel.objects.all()
        stations_dict = {
            (round(float(s.latitude), 4), round(float(s.longitude), 4)): s.id
            for s in stations
        }

        expected_stations = y * x
        if len(stations_dict) != expected_stations:
            raise ValueError(
                f"تعداد ایستگاه‌ها در دیتابیس ({len(stations_dict)}) با فایل nc ({expected_stations}) مطابقت ندارد"
            )
    except Exception as e:
        logger.exception("error in loading stations: %s", e)
        return

    # گرفتن زمان‌ها
    try:
        times_raw = ds['times'].values
        if isinstance(times_raw[0], bytes):
            times = pd.to_datetime([t.decode('utf-8') for t in times_raw])
        else:
            times = pd.to_datetime(times_raw)
    except Exception as e:
        logger.exception("error in parsing times: %s", e)
        return

    # محاسبه مختصات و مچ کردن ID ایستگاه‌ها
    try:
        coords = [
            (round(float(lat[i, j]), 4), round(float(lon[i, j]), 4))
            for i in range(y) for j in range(x)
        ]
        station_ids = [stations_dict[coord] for coord in coords]
    except KeyError as e:
        logger.exception("coordinate not found in station_dict: %s", e)
        return

    # ساخت دیتافریم هواشناسی
    try:
        n_stations = y * x
        n_times = len(times)

        weather_df = pd.DataFrame({
            'station_id': np.repeat(station_ids, n_times),
            'forecast_time': np.tile(times, n_stations),
            'temperature': ds['temperature'].values.reshape(-1),
            'wind_speed': ds['wind_speed'].values.reshape(-1),
            'wind_direction': ds['wind_direction'].values.reshape(-1),
        })

        logger.info("weather dataframe created with shape: %s", weather_df.shape)
    except Exception as e:
        logger.exception("error in creating weather dataframe: %s", e)
        return

    # انتقال به دیتابیس
    try:
        weather_io = StringIO()
        weather_df.to_csv(weather_io, index=False)
        weather_io.seek(0)

        weather_mapping = CopyMapping(
            WindForecastModel,
            weather_io,
            dict(
                station_id='station_id',
                forecast_time='forecast_time',
                temperature='temperature',
                wind_speed='wind_speed',
                wind_direction='wind_direction',
            )
        )
        weather_mapping.save()
        logger.info("weather data saved to database successfully.")
    except Exception as e:
        logger.exception("error in saving weather data to database: %s", e)
        return