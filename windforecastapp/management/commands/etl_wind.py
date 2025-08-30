from django.core.management.base import BaseCommand
# from windforecastapp.utils.move_wind_data_to_db import move_to_db
from windforecastapp.utils.ETL_wind_utils import etl_netcdf_to_db
import time





# تنظیمات
CHUNK_SIZE = 500000  # تعداد ردیف forecast در هر batch (قابل تنظیم)
STATION_BATCH = 5000  # batch برای bulk_create ایستگاه‌ها

class Command(BaseCommand):
    help = "Load wind data from netCDF into DB using CopyMapping (chunked, memory-safe)."

    # def add_arguments(self, parser):
    #     parser.add_argument('nc_path', type=str, help='Path to merged_nc_file.nc')
    #     parser.add_argument('--chunk_size', type=int, default=CHUNK_SIZE)

    def handle(self, *args, **options):
        try:
            start = time.time()
            nc_path = 'D:\\project\\TotalDB\\TOTALDB_CYCLES\\wind\\gfs.2025081012\\merged_nc_file.nc'
            etl_netcdf_to_db(nc_path)
            self.stdout.write(
                self.style.SUCCESS(f"execution time: {time.time() - start:.2f} s")
            )
        except Exception as e:
            self.stderr.write(
            self.style.ERROR(f'exception in convert nc file:{e}')
            )
