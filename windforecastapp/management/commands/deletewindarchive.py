from django.core.management.base import BaseCommand
# from windforecastapp.utils.move_data_to_db import move_to_db
from windforecastapp.models import WindForecastModel, WindStationModel
import time


class Command(BaseCommand):
    help = 'Delete all data in wind archive'

    def handle(self, *args, **options):

        try:
           
            self.stdout.write(
                self.style.SUCCESS('delete wind archive successfully')
            )
            # start = time.time()
            # move_to_db(file_path)
            # print(f"execution time: {time.time() - start:.2f} s")
        except Exception as e:
            self.stderr.write(
            self.style.ERROR(f'{e}')
            )
            
        
        # self.stdout.write(
        #     self.style.SUCCESS('convert compeleted!')
        # )

