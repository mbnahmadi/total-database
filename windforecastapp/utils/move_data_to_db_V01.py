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

# ---------- Main Function ----------
def move_to_db(file_path):
    logger.info("start processing file: %s", file_path)

    if not os.path.isfile(file_path):
        logger.error("file not found: %s", file_path)
        return

    try:
        ds = xr.open_dataset(file_path, engine='netcdf4')
    except Exception as e:
        logger.exception("error in opening netcdf file: %s", e)
        return

    try:
        lat = ds['lat'].values
        lon = ds['lon'].values
        y, x = lat.shape
        logger.info("network dimensions: %d × %d", y, x)

    except Exception as e:
        logger.exception("error in extracting coordinates: %s", e)
        return

    try:
        if not WindStationModel.objects.exists():
            logger.info("no station found, start creating stations...")

            stations_df = pd.DataFrame({
                'location': [Point(float(lon[i, j]), float(lat[i, j])) for i in range(y) for j in range(x)],
                'name': [f"Station_{i}" for i in range(y * x)],
                'description': [''] * (y * x),
            })

            # ذخیره یک‌به‌یک چون PointField قابل copy_mapping نیست
            station_objs = [
                WindStationModel(location=row['location'], name=row['name'], description=row['description'])
                for _, row in stations_df.iterrows()
            ]
            WindStationModel.objects.bulk_create(station_objs, batch_size=1000)
            logger.info("stations created successfully.")
    except Exception as e:
        logger.exception("error in creating or inserting stations: %s", e)
        return

    try:
        WindForecastModel.objects.all().delete()
        logger.info("last cycle weather data deleted successfully.")
    except Exception as e:
        logger.exception("error in deleting weather data: %s", e)
        return
    try:
        # ساخت دیکشنری از مختصات گرد شده به station.id
        stations = WindStationModel.objects.all()
        stations_dict = {
            (round(s.location.y, 4), round(s.location.x, 4)): s.id for s in stations
        }

        expected_stations = y * x
        if len(stations_dict) != expected_stations:
            raise ValueError(f"number of stations in database ({len(stations_dict)}) does not match the number of stations in the file ({expected_stations})")
    except Exception as e:
        logger.exception("error in checking stations: %s", e)
        return

    try:
        time_bytes = ds['time_str'].values
        time_str = [t.decode('utf-8') for t in time_bytes]
        times = pd.to_datetime(time_str, format='%Y-%m-%d_%H:%M:%S')
    except Exception as e:
        logger.exception("error in converting time: %s", e)
        return

    try:
        coords = [
            (round(float(lat[i, j]), 4), round(float(lon[i, j]), 4))
            for i in range(y) for j in range(x)
        ]

        try:
            station_ids = [stations_dict[coord] for coord in coords]
        except KeyError as e:
            logger.exception("coordinates in nc file (%s) does not match the database", e)
            return

        n_stations = y * x
        n_times = len(times)

        weather_df = pd.DataFrame({
            'station_id': np.repeat(station_ids, n_times),
            'forecast_time': np.tile(times, n_stations),
            'T2': ds['T2'].values.reshape(-1),
            'U10': ds['U10'].values.reshape(-1),
            'V10': ds['V10'].values.reshape(-1),
            'Q2': ds['Q2'].values.reshape(-1),
            'RAINNC': ds['RAINC'].values.reshape(-1),
            'PSFC': ds['PSFC'].values.reshape(-1),
        })

        weather_io = StringIO()
        weather_df.to_csv(weather_io, index=False)
        weather_io.seek(0)

        weather_mapping = CopyMapping(
            WindForecastModel,
            weather_io,
            dict(
                station_id='station_id',
                forecast_time='forecast_time',
                T2='T2',
                U10='U10',
                V10='V10',
                Q2='Q2',
                RAINNC='RAINNC',
                PSFC='PSFC',
            )
        )
        weather_mapping.save()

        logger.info("weather data transferred to database successfully.")
    except Exception as e:
        logger.exception("error in processing or inserting weather data: %s", e)
        return

    try:
        del ds, weather_df, weather_io
        gc.collect()
        logger.info("memory cleaned.")
    except Exception as e:
        logger.warning("error in cleaning memory: %s", e)