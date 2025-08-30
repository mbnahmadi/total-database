from django.db import models
from django.contrib.gis.db import models as gis_models
from postgres_copy import CopyManager
from django.utils.translation import gettext_lazy as _

# Create your models here.

class WaveStationModel(models.Model):
    location = gis_models.PointField(geography=True, verbose_name=_("location"))
    name = models.CharField(max_length=255, verbose_name=_("name"), null=True, blank=True, unique=True)
    description = models.TextField(verbose_name=_("description"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created_at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    @property
    def latitude(self):
        return self.location.y

    @property
    def longitude(self):
        return self.location.x

    def __str__(self):
        return f"{self.name} - {self.location}"

    class Meta:
        verbose_name = _("wave station")
        verbose_name_plural = _("wave stations")
        constraints = [
            models.UniqueConstraint(fields=["location"], name="unique_wave_location")
        ]
        indexes = [
            # models.Index(fields=["location"]),
            gis_models.Index(fields=['location'], name='wave_location_gist_idx')  # GiST index
        ]

    def __str__(self):
        return f"{self.name} - {self.latitude} - {self.longitude}"

class WaveForecastModel(models.Model):
    station = models.ForeignKey(WaveStationModel, on_delete=models.CASCADE, related_name="forecast", verbose_name=_("station"))
    forecast_time = models.DateTimeField(verbose_name=_("forecast_time"))
    tp = models.FloatField(verbose_name=_("Tp"), help_text='from tab01') #
    hs = models.FloatField(verbose_name=_("Hs"), help_text='from tab41/ Unit(m)') #  
    hmax = models.FloatField(verbose_name=_("Hmax"), help_text='Hs * 1.8/ Unit(m)') #  
    tz = models.FloatField(verbose_name=_("Tz"), help_text='Tr from tab41') #
    wave_direction = models.FloatField(verbose_name=_("wave_direction"), help_text='from tab41') #


    def __str__(self):
        return f"{self.station.name} - {self.forecast_time}"

    class Meta:
        
        indexes = [
            models.Index(fields=["forecast_time", "station"]),
            models.Index(fields=["station"]),
            models.Index(fields=["forecast_time"]),
        ]
        

    objects = CopyManager() 


class WaveArchiveModel(models.Model):
    station = models.ForeignKey(WaveStationModel, on_delete=models.CASCADE, related_name="archive", verbose_name=_("station"))
    forecast_time = models.DateTimeField(verbose_name=_("forecast_time"))
    tp = models.FloatField(verbose_name=_("Tp"), help_text='from tab01') #
    hs = models.FloatField(verbose_name=_("Hs"), help_text='from tab41/ Unit(m)') #  
    hmax = models.FloatField(verbose_name=_("Hmax"), help_text='Hs * 1.8/ Unit(m)') #  
    tz = models.FloatField(verbose_name=_("Tz"), help_text='Tr from tab41') #
    wave_direction = models.FloatField(verbose_name=_("wave_direction"), help_text='from tab41') #

    def __str__(self):
        return f"{self.station.name} - {self.forecast_time}"

    class Meta:
        # unique_together = ("station", "forecast_time")
        indexes = [
            models.Index(fields=["forecast_time", "station"]),
            models.Index(fields=["station"]),
            models.Index(fields=["forecast_time"]),
        ]
    objects = CopyManager() 
