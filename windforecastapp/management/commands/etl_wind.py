from django.core.management.base import BaseCommand
# from windforecastapp.utils.move_wind_data_to_db import move_to_db
from windforecastapp.utils.ETL_wind_utils import etl_netcdf_to_db
import time

class Command(BaseCommand):
    help = "Load wind data from netCDF into DB using CopyMapping (chunked, memory-safe)."

    def handle(self, *args, **options):
        try:
            start = time.time()
            nc_path = 'D:\\project\\TotalDB\\TOTALDB_CYCLES\\wind\\PersianGulf\\2025101412\\merged_nc_file.nc'
            etl_netcdf_to_db(nc_path)
            self.stdout.write(
                self.style.SUCCESS(f"execution time: {time.time() - start:.2f} s")
            )
        except Exception as e:
            self.stderr.write(
            self.style.ERROR(f'exception in convert nc file:{e}')
            )
