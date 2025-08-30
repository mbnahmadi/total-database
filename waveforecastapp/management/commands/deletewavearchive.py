from django.core.management.base import BaseCommand
# from windforecastapp.utils.move_data_to_db import move_to_db
from waveforecastapp.models import WaveArchiveModel, WaveStationModel
import time


class Command(BaseCommand):
    help = 'Delete all data in wave archive'

    def handle(self, *args, **options):

        try:
            WaveStationModel.objects.all().delete()
            WaveArchiveModel.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('delete wave archive successfully')
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

