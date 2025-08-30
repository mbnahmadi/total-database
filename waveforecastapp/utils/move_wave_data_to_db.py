import os
import logging
import pandas as pd
import numpy as np
from io import StringIO
from django.contrib.gis.geos import Point
from waveforecastapp.models import WaveStationModel, WaveForecastModel, WaveArchiveModel
from postgres_copy import CopyMapping

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("wave_import.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def move_wave_to_db(tab01_path, tab41_path):
    logger.info("start reading files...")

    if not os.path.isfile(tab01_path) or not os.path.isfile(tab41_path):
        logger.error("One or both CSV files not found.")
        return


    try:
        df01 = pd.read_csv(tab01_path, skiprows=2)
        df41 = pd.read_csv(tab41_path, skiprows=2)
    except Exception as e:
        logger.exception("error in reading CSV files: %s", e)
        return

    try:
        # استانداردسازی نام ستون‌ها
        df01.columns = ['forecast_time', 'lon', 'lat', 'U10_01', 'wave_direction_01', 'Hs_01', 'Tp_01']
        df41.columns = ['forecast_time', 'lon', 'lat', 'Hs_41', 'L_41', 'Tr_41', 'wave_direction_41',
                        'Spr_41', 'fp_41', 'p_dir_41', 'p_spr_41']

        # تبدیل زمان به datetime
        df01['forecast_time'] = pd.to_datetime(df01['forecast_time'],  format='%Y/%m/%d %H:%M:%S')
        # print(df01['forecast_time'])
        df41['forecast_time'] = pd.to_datetime(df41['forecast_time'],  format='%Y/%m/%d %H:%M:%S')
        # print('----------------')
        # print(df41['forecast_time'])


        # ادغام روی lat/lon/time
        merged_df = pd.merge(df01, df41, on=['forecast_time', 'lat', 'lon'])

    except Exception as e:
        logger.exception("error in merging data: %s", e)
        return
    
    try:
        WaveForecastModel.objects.all().delete()
        logger.info("last cycle wave data deleted successfully.")
    except Exception as e:
        logger.exception("error in deleting wave data: %s", e)
        return


    try:
        # ساخت ایستگاه‌ها در صورت نیاز
        stations = WaveStationModel.objects.all()
        if not stations.exists():
            logger.info("no wave station found. creating wave stations...")

            station_objs = [
                WaveStationModel(
                    location=Point(round(row['lon'], 4), round(row['lat'], 4)),
                    name=f"WaveStation_{i}",
                    description=""
                )
                for i, row in merged_df[['lat', 'lon']].drop_duplicates().iterrows()
            ]
            WaveStationModel.objects.bulk_create(station_objs, batch_size=1000)
            logger.info("wave stations created successfully.")

        # ساخت دیکشنری از مختصات به station_id
        stations = WaveStationModel.objects.all()
        stations_dict = {
            (round(s.location.y, 4), round(s.location.x, 4)): s.id for s in stations
        }

        # اضافه کردن station_id به merged_df
        merged_df['station_id'] = merged_df.apply(
            lambda row: stations_dict.get((round(row['lat'], 4), round(row['lon'], 4))), axis=1
        )

        if merged_df['station_id'].isnull().any():
            raise ValueError("some coordinates don't match any station in DB")

        # فیلدهایی که قراره در مدل ذخیره بشن
        wave_df = merged_df[[
            'station_id', 'forecast_time',
            'U10_01', 'wave_direction_01', 'Tp_01', 'Hs_01',
            'Hs_41', 'L_41', 'Tr_41', 'wave_direction_41',
            'Spr_41', 'fp_41', 'p_dir_41', 'p_spr_41'
        ]]

        # انتقال داده با CopyMapping
        buffer = StringIO()
        wave_df.to_csv(buffer, index=False)
        buffer.seek(0)

        mapping = CopyMapping(
            WaveForecastModel,
            buffer,
            dict(
                station_id='station_id',
                forecast_time='forecast_time',
                U10_01='U10_01',
                wave_direction_01='wave_direction_01',
                Tp_01='Tp_01',
                Hs_01='Hs_01',
                Hs_41='Hs_41',
                L_41='L_41',
                Tr_41='Tr_41',
                wave_direction_41='wave_direction_41',
                Spr_41='Spr_41',
                fp_41='fp_41',
                p_dir_41='p_dir_41',
                p_spr_41='p_spr_41',
            )
        )
        mapping.save()
        logger.info("wave forecast data inserted successfully.")

    except Exception as e:
        logger.exception("error in processing wave data: %s", e)
        return
    
    # --------------------------------
    # استخراج داده‌های آرشیو ۱۲ ساعت اول
    # --------------------------------
    
    first_time = wave_df['forecast_time'].min()
    twelve_hour_limit = first_time + pd.Timedelta(hours=12)

    archive_df = wave_df[wave_df['forecast_time'] < twelve_hour_limit]

    archive_buffer = StringIO()
    archive_df.to_csv(archive_buffer, index=False)
    archive_buffer.seek(0)

    archive_mapping = CopyMapping(
        WaveArchiveModel,
        archive_buffer,
        dict(
            station_id='station_id',
            forecast_time='forecast_time',
            U10_01='U10_01',
            wave_direction_01='wave_direction_01',
            Tp_01='Tp_01',
            Hs_01='Hs_01',
            Hs_41='Hs_41',
            L_41='L_41',
            Tr_41='Tr_41',
            wave_direction_41='wave_direction_41',
            Spr_41='Spr_41',
            fp_41='fp_41',
            p_dir_41='p_dir_41',
            p_spr_41='p_spr_41',
        )
    )
    archive_mapping.save()
    logger.info("12-hour wave archive inserted successfully.")
