from django.core.management.base import BaseCommand
from windforecastapp.models import WindStationModel
import time


class Command(BaseCommand):
    help = 'Delete all data in wind archive'

    def handle(self, *args, **options):

        try:
            start = time.time()
            WindStationModel.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"delete wind stations successfully and execution time: {time.time() - start:.2f} s")
            )

        except Exception as e:
            self.stderr.write(
            self.style.ERROR(f'{e}')
            )
