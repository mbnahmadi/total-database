from django.core.management.base import BaseCommand
# from windforecastapp.utils.move_data_to_db import move_to_db
from waveforecastapp.models import WaveStationModel, WaveForecastModel, WaveArchiveModel


class Command(BaseCommand):
    help = 'transfer data from nc file to database'

    def handle(self, *args, **options):
        # file_path = 'F:\\merged_gfs.2025070200.nc'

        try:
            WaveArchiveModel.objects.all().delete()
            WaveForecastModel.objects.all().delete()
            WaveStationModel.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS('delete wave location successfully')
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

