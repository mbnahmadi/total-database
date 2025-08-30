import gc
import logging
import io
import pandas as pd
import xarray as xr
from django.db import transaction, connection
from postgres_copy import CopyMapping
from django.contrib.gis.geos import Point
from windforecastapp.models import WindStationModel, WindForecastModel, WindArchiveModel


# ----------- logging --------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("weather_import.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
# ---------------------------------------

CHUNK_SIZE = 500000
STATION_BATCH = 10000

def ensure_index_exists(table_name, index_name, index_type, column_name):
    with connection.cursor() as cursor:
        cursor.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = '{table_name}'
                    AND indexname = '{index_name}'
                ) THEN
                    EXECUTE 'CREATE INDEX {index_name} ON "{table_name}" USING {index_type} ({column_name})';
                END IF;
            END$$;
        """)


def ensure_btree_index(table_name, index_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = '{table_name}'
                    AND indexname = '{index_name}'
                ) THEN
                    EXECUTE 'CREATE INDEX {index_name} ON "{table_name}" ({column_name})';
                END IF;
            END$$;
        """)


def cluster_table_on_index(table_name, index_name):
    with connection.cursor() as cursor:
        cursor.execute(f'CLUSTER "{table_name}" USING {index_name};')
        logger.info(f"Clustered table {table_name} using index {index_name}")


def periodic_reindex(index_name, days_threshold=7):
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT
                    NOW() - COALESCE(pg_stat_all_indexes.last_vacuum, NOW()) AS since_last_vacuum
                FROM pg_stat_all_indexes
                WHERE indexrelname = '{index_name}'
                LIMIT 1;
            """)
            result = cursor.fetchone()
            if result and result[0].days >= days_threshold:
                cursor.execute(f'REINDEX INDEX {index_name};')
                logger.info(f"Reindexed {index_name} after {result[0].days} days.")
    except Exception as e:
        logger.exception(f"Error in periodic REINDEX for {index_name}: {e}")


def etl_netcdf_to_db(nc_path):
    logger.info(f"Opening dataset: {nc_path}")
    ds = xr.open_dataset(nc_path)

    logger.info("Converting dataset to DataFrame...")
    df = ds.to_dataframe().reset_index()
    df = df.drop_duplicates(subset=['lat', 'lon', 'time'])
    logger.info(f"DataFrame shape after drop_duplicates: {df.shape}")

    # ساخت station_id بر اساس lat/lon
    df['station_id'] = pd.factorize(list(zip(df['lat'], df['lon'])))[0] + 1

    # استخراج ایستگاه‌ها
    stations_df = df[['station_id', 'lat', 'lon']].drop_duplicates().sort_values('station_id').reset_index(drop=True)
    logger.info(f"Unique stations: {len(stations_df)}")

    try:
        existing_coords_qs = WindStationModel.objects.values_list('location', flat=True)
        existing_coords = set(existing_coords_qs)
        new_station_objs = []
        for _, row in stations_df.iterrows():
            p = Point(row['lon'], row['lat'], srid=4326)
            if p not in existing_coords:
                new_station_objs.append(WindStationModel(
                    id=int(row['station_id']),
                    location=p,
                    name=f"station_{int(row['station_id'])}"
                ))
        if new_station_objs:
            logger.info(f"Inserting {len(new_station_objs)} new stations...")
            with transaction.atomic():
                for i in range(0, len(new_station_objs), STATION_BATCH):
                    batch = new_station_objs[i:i + STATION_BATCH]
                    WindStationModel.objects.bulk_create(batch, ignore_conflicts=True, batch_size=STATION_BATCH)
            del new_station_objs
            gc.collect()
        else:
            logger.info("No new stations to insert.")
    except Exception as e:
        logger.exception(f"Error creating/inserting stations: {e}")

    # DataFrame مربوط به forecast
    forecast_df = df.drop(columns=['lat', 'lon']).rename(columns={
        'time': 'forecast_time',
        'T2': 'temperature',
        'WS10': 'ws10',
        'WG10': 'wg10',
        'WS50': 'ws50',
        'WG50': 'wg50'
    }).sort_values(by=['station_id', 'forecast_time']).reset_index(drop=True)

    # آرشیو ۱۲ ساعت اول
    first_time = forecast_df['forecast_time'].min()
    twelve_hours_later = first_time + pd.Timedelta(hours=12)
    archive_df = forecast_df[forecast_df['forecast_time'] <= twelve_hours_later].copy()

    logger.info(f"Forecast rows: {len(forecast_df)}")
    logger.info(f"Archive rows (first 12h): {len(archive_df)}")

    del df
    gc.collect()

    mapping = {
        'station_id': 'station_id',
        'forecast_time': 'forecast_time',
        'temperature': 'temperature',
        'ws10': 'ws10',
        'wind_direction': 'wind_direction',
        'wg10': 'wg10',
        'ws50': 'ws50',
        'wg50': 'wg50',
    }

    try:
        # پاک کردن داده‌های قبلی forecast با TRUNCATE
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(f'TRUNCATE TABLE "{WindForecastModel._meta.db_table}" RESTART IDENTITY CASCADE;') #CASCADE ینی اگه جدول فارن کی هم داشته باشه خالی میشه
            logger.info("WindForecastModel truncated successfully.")

            # درج forecast
            logger.info("Inserting forecast data...")
            for start in range(0, len(forecast_df), CHUNK_SIZE):
                end = min(start + CHUNK_SIZE, len(forecast_df))
                chunk = forecast_df.iloc[start:end].copy()
                if chunk['forecast_time'].dtype.kind in ('M', 'm'):
                    chunk['forecast_time'] = chunk['forecast_time'].dt.strftime('%Y-%m-%d %H:%M:%S')

                csv_buffer = io.StringIO()
                chunk.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                CopyMapping(WindForecastModel, csv_buffer, mapping).save()
                csv_buffer.close()
                del chunk, csv_buffer
                gc.collect()

            # درج archive
            logger.info("Inserting archive data...")
            for start in range(0, len(archive_df), CHUNK_SIZE):
                end = min(start + CHUNK_SIZE, len(archive_df))
                chunk = archive_df.iloc[start:end].copy()
                if chunk['forecast_time'].dtype.kind in ('M', 'm'):
                    chunk['forecast_time'] = chunk['forecast_time'].dt.strftime('%Y-%m-%d %H:%M:%S')

                csv_buffer = io.StringIO()
                chunk.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                CopyMapping(WindArchiveModel, csv_buffer, mapping).save()
                csv_buffer.close()
                del chunk, csv_buffer
                gc.collect()

    except Exception as e:
        logger.exception(f"Error inserting forecast/archive data: {e}")

    del forecast_df, archive_df
    gc.collect()

    # مدیریت ایندکس‌ها و کلستر و ریندکس
    station_table = WindStationModel._meta.db_table
    forecast_table = WindForecastModel._meta.db_table
    archive_table = WindArchiveModel._meta.db_table

    try:
        ensure_index_exists(station_table, 'windstation_location_gist', 'GIST', 'location')
        ensure_btree_index(forecast_table, 'windforecast_forecast_time_idx', 'forecast_time')
        ensure_btree_index(archive_table, 'windarchive_forecast_time_idx', 'forecast_time')

        cluster_table_on_index(station_table, 'windstation_location_gist')

        # periodic_reindex('windstation_location_gist', days_threshold=7)
        # periodic_reindex('windforecast_forecast_time_idx', days_threshold=7)
        # periodic_reindex('windarchive_forecast_time_idx', days_threshold=7)

    except Exception as e:
        logger.exception(f"Error managing indexes, clustering, or reindexing: {e}")

    logger.info("ETL completed successfully.")