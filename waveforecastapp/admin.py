from django.contrib import admin    
from .models import WaveStationModel, WaveForecastModel, WaveArchiveModel
# from windforecastapp.forms import WindStationForm

# Register your models here.
@admin.register(WaveStationModel)
class WaveStationModelAdmin(admin.ModelAdmin):
    # form = WindStationForm
    list_display = ("name", "location")
    # list_filter = ("created_at", "updated_at", "name")
    search_fields = ("name", "location")
    list_per_page = 100
    list_max_show_all = 100

    
    def latitude_display(self, obj):
        return round(obj.latitude, 5)
    latitude_display.short_description = "Latitude"  

    def Longitude_display(self, obj):
        return round(obj.longitude, 5)
    Longitude_display.short_description = "Longitude"   


@admin.register(WaveForecastModel)
class WaveForecastModelAdmin(admin.ModelAdmin):
    list_display = ("station", "forecast_time")
    # list_filter = ("forecast_time", "station")
    search_fields = ("station__name", "forecast_time")
    list_per_page = 1000
    list_max_show_all = 1000


@admin.register(WaveArchiveModel)
class WaveArcgiveModelAdmin(admin.ModelAdmin):
    list_display = ("station", "forecast_time")
    # list_filter = ("forecast_time", "station")
    search_fields = ("station__name", "forecast_time")
    list_per_page = 1000
    list_max_show_all = 1000

  