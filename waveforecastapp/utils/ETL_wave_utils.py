# ETL -> Extract, Transform, and Load

import os
import logging
import pandas as pd
import numpy as np
from io import StringIO
import io
import gc
from datetime import timedelta
from django.contrib.gis.geos import Point
from django.db import transaction, connection
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

STATION_BATCH = 10000
CHUNK_SIZE = 500000

def ensure_index_exists(table_name, index_name, index_type, column_name):
    with connection.cursor() as cursor:
        cursor.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname='{index_name}') THEN
                    CREATE INDEX {index_name} ON {table_name} USING {index_type} ({column_name});
                END IF;
            END$$;
        """)

def cluster_table_on_index(table_name, index_name):
    with connection.cursor() as cursor:
        cursor.execute(f"CLUSTER {table_name} USING {index_name};")

def etl_csv_to_db(tab01_path, tab41_path):
    logger.info("Starting Wave ETL...")

    # --- خواندن CSVها ---
    df_tab01 = pd.read_csv(tab01_path, skiprows=[1])
    df_tab01 = df_tab01[["Time","Long","Lat","Tp"]]
    df_tab01["Time"] = pd.to_datetime(df_tab01["Time"], format="%Y/%m/%d %H:%M:%S")

    df_tab41 = pd.read_csv(tab41_path, skiprows=[1])
    df_tab41 = df_tab41[["Hs","Tr","Dir"]]
    df_tab41["Hs"] = pd.to_numeric(df_tab41["Hs"], errors='coerce')
    df_tab41["Tr"] = pd.to_numeric(df_tab41["Tr"], errors='coerce')
    df_tab41["Dir"] = pd.to_numeric(df_tab41["Dir"], errors='coerce')
    df_tab41["Hmax"] = df_tab41["Hs"] * 1.8

    # --- ادغام فایل‌ها ---
    df_merged = pd.concat([df_tab01, df_tab41], axis=1)
    df_merged['station_id'] = pd.factorize(list(zip(df_merged['Lat'], df_merged['Long'])))[0] + 1
    df_merged = df_merged.sort_values(by=['station_id', 'Time']).reset_index(drop=True)

    # --- ساخت جدول ایستگاه‌ها ---
    stations_df = df_merged[['station_id', 'Lat', 'Long']].drop_duplicates().sort_values(by='station_id').reset_index(drop=True)
    existing_coords = set(WaveStationModel.objects.values_list('location', flat=True))
    new_stations = []

    for _, row in stations_df.iterrows():
        point = Point(row['Long'], row['Lat'], srid=4326)
        if point not in existing_coords:
            new_stations.append(
                WaveStationModel(
                    id=int(row['station_id']),
                    location=point,
                    name=f"wave_station_{int(row['station_id'])}"
                )
            )

    if new_stations:
        logger.info("Inserting %d new wave stations...", len(new_stations))
        with transaction.atomic():
            for i in range(0, len(new_stations), STATION_BATCH):
                batch = new_stations[i:i+STATION_BATCH]
                WaveStationModel.objects.bulk_create(batch, ignore_conflicts=True, batch_size=STATION_BATCH)
                logger.info("Inserted station batch %d-%d", i, i+len(batch))
        del new_stations
        gc.collect()
    else:
        logger.info("No new wave stations to insert.")

    # --- آماده‌سازی داده‌ها ---
    data_df = df_merged.drop(columns=['Lat', 'Long']).sort_values(by=['station_id', 'Time']).reset_index(drop=True)

    mapping_forecast = {
        'station_id': 'station_id',
        'forecast_time': 'Time',
        'tp': 'Tp',
        'hs': 'Hs',
        'hmax': 'Hmax',
        'tz': 'Tr',
        'wave_direction': 'Dir'
    }

    # --- پاک کردن جدول‌ها و درج داده‌ها ---
    logger.info("Truncating WaveForecastModel table...")
    with connection.cursor() as cursor:
        cursor.execute(f'TRUNCATE TABLE "{WaveForecastModel._meta.db_table}" RESTART IDENTITY CASCADE;')
    logger.info("WaveForecastModel truncated successfully.")


    # logger.info("Clearing WaveForecastModel table...")
    # with transaction.atomic():
    #     WaveForecastModel.objects.all().delete()

    logger.info("Inserting WaveForecastModel data in chunks...")
    for start in range(0, len(data_df), CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, len(data_df))
        chunk = data_df.iloc[start:end].copy()
        chunk['Time'] = chunk['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        csv_buffer = io.StringIO()
        chunk.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        cm = CopyMapping(WaveForecastModel, csv_buffer, mapping_forecast)
        cm.save()
        csv_buffer.close()
        del chunk, csv_buffer
        gc.collect()
        logger.info("Inserted forecast chunk %d-%d", start, end)

    # --- آرشیو: ۱۲ ساعت اول ---
    first_time = data_df['Time'].min()
    twelve_hours_later = first_time + timedelta(hours=11)
    archive_df = data_df[data_df['Time'] <= twelve_hours_later].copy()

    mapping_archive = mapping_forecast.copy()
    # logger.info("Clearing WaveArchiveModel table...")
    # with transaction.atomic():
    #     WaveArchiveModel.objects.all().delete()

    logger.info("Inserting WaveArchiveModel data (first 12h)...")
    for start in range(0, len(archive_df), CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, len(archive_df))
        chunk = archive_df.iloc[start:end].copy()
        chunk['Time'] = chunk['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        csv_buffer = io.StringIO()
        chunk.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        cm = CopyMapping(WaveArchiveModel, csv_buffer, mapping_archive)
        cm.save()
        csv_buffer.close()
        del chunk, csv_buffer
        gc.collect()
        logger.info("Inserted archive chunk %d-%d", start, end)

    # --- ایندکس‌ها و Clustering ---
    try:
        ensure_index_exists(WaveStationModel._meta.db_table, 'wave_location_gist_idx', 'GIST', 'location')
        ensure_index_exists(WaveForecastModel._meta.db_table, 'waveforecast_forecast_time_idx', 'BTREE', 'forecast_time')
        ensure_index_exists(WaveArchiveModel._meta.db_table, 'wavearchive_forecast_time_idx', 'BTREE', 'forecast_time')

        cluster_table_on_index(WaveStationModel._meta.db_table, 'wave_location_gist_idx')
        logger.info("Indexes and clustering applied successfully.")
    except Exception as e:
        logger.exception("Error managing indexes or clustering: %s", e)

    logger.info("Wave ETL completed successfully.")