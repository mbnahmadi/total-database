from django.db import models
from django.contrib.gis.db import models as gis_models
from postgres_copy import CopyManager
from django.utils.translation import gettext_lazy as _

# Create your models here.

class WindStationModel(models.Model):
    location = gis_models.PointField(geography=True, verbose_name=_("location"))#این نقطه جغرافیایی، روی کره‌ی زمین در نظر گرفته شود، نه روی یک صفحه‌ی صاف دوبعدیgeography=True 
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
    
    objects = CopyManager() 

    class Meta:
        verbose_name = _("wind station")
        verbose_name_plural = _("wind stations")
        ordering = ["name"]

        # unique_together = ("latitude", "longitude")
        # برای داده هایی مثه location نمیتونیم از unique_together استفاده کنیم
        constraints = [
            models.UniqueConstraint(fields=["location"], name="unique_location")
        ]
        indexes = [
            # models.Index(fields=["location"]),
            gis_models.Index(fields=['location'], name='location_gist_idx')  # GiST index
        ]
    def __str__(self):
        return f"{self.name} - {self.latitude} - {self.longitude}"



class WindForecastModel(models.Model):
    # اگه مدل stations پاک شه داده های این جدولم پاک میشه
    station = models.ForeignKey(WindStationModel, on_delete=models.CASCADE, verbose_name=_("wind station"), related_name="forecasts")
    forecast_time = models.DateTimeField(verbose_name=_("forecast_time"))
    temperature = models.FloatField(verbose_name=_("temperature"), help_text=_("Temperature at 2 meters above ground"))
    ws10 = models.FloatField(verbose_name=_("ws10"))
    wind_direction = models.FloatField(verbose_name=_("wind_direction"))
    wg10 = models.FloatField(verbose_name=_("wg10"))
    ws50 = models.FloatField(verbose_name=_("ws50"))
    wg50 = models.FloatField(verbose_name=_("wg50"))

    objects = CopyManager()    
    
    class Meta:
        unique_together = ("station", "forecast_time")
        indexes = [
            models.Index(fields=["forecast_time", "station"]),
        ]

    def __str__(self):
        return f"{self.station.name} - {self.forecast_time}"

class WindArchiveModel(models.Model):
    station = models.ForeignKey(WindStationModel, on_delete=models.CASCADE, verbose_name=_("wind station"), related_name='archive')
    forecast_time = models.DateTimeField(verbose_name=_("forecast_time"))
    temperature = models.FloatField(verbose_name=_("temperature"), help_text=_("Temperature at 2 meters above ground"))
    ws10 = models.FloatField(verbose_name=_("ws10"))
    wind_direction = models.FloatField(verbose_name=_("wind_direction"))
    wg10 = models.FloatField(verbose_name=_("wg10"))
    ws50 = models.FloatField(verbose_name=_("ws50"))
    wg50 = models.FloatField(verbose_name=_("wg50"))


    def __str__(self):
        return f"{self.station.name} - {self.forecast_time}"

    class Meta:
        verbose_name = _("wind archive")
        verbose_name_plural = _("wind archives")
        indexes = [
            models.Index(fields=["forecast_time", "station"]),
            models.Index(fields=["station"]),
            models.Index(fields=["forecast_time"]),
        ]
    objects = CopyManager()    
