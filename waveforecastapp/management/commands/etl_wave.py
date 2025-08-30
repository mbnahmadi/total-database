from django.core.management.base import BaseCommand
from waveforecastapp.utils.move_wave_data_to_db import move_wave_to_db
from waveforecastapp.utils.ETL_wave_utils import etl_csv_to_db
import time


class Command(BaseCommand):
    help = 'transfer data from nc file to database'

    def handle(self, *args, **options):
        # file_path = 'G:\\MOBIN\\TOTALDB_CYCLES\\wave\\gfs.2025071800'
        # file_path_01 = 'G:\\MOBIN\\TOTALDB_CYCLES\\wave\\gfs.2025072112\\tab01.csv'
        # file_path_41 = 'G:\\MOBIN\\TOTALDB_CYCLES\\wave\\gfs.2025072112\\tab41.csv'

        tab01_path = 'D:\\project\\TotalDB\\TOTALDB_CYCLES\\wave\\gfs.2025081112\\tab01.csv'
        tab41_path = 'D:\\project\\TotalDB\\TOTALDB_CYCLES\\wave\\gfs.2025081112\\tab41.csv'


        try:
            start = time.time()
            # move_wave_to_db(file_path_01, file_path_41)
            etl_csv_to_db(tab01_path, tab41_path)
            self.stdout.write(
                self.style.SUCCESS(f"execution time: {time.time() - start:.2f} s")
            )
        except Exception as e:
            self.stderr.write(
            self.style.ERROR(f'{e}')
            )
            
        

