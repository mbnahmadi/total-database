from django.contrib import admin
from .models import WindStationModel, WindForecastModel, WindArchiveModel
# from .forms import WindStationForm

# Register your models here.
@admin.register(WindStationModel)
class WindStationModelAdmin(admin.ModelAdmin):
    # form = WindStationForm
    # list_display = ("id", "latitude_display", "Longitude_display")
    list_display = ["latitude", "longitude"]
    # search_fields = ("name", "location")
    list_per_page = 100
    list_max_show_all = 100

    # def latitude_display(self, obj):
    #     return round(obj.latitude, 5)
    # latitude_display.short_description = "Latitude"  

    # def Longitude_display(self, obj):
    #     return round(obj.longitude, 5)
    # Longitude_display.short_description = "Longitude"   

@admin.register(WindForecastModel)
class WindForecastModelAdmin(admin.ModelAdmin):
    list_display = ("station_id", "station", "forecast_time")
    # list_filter = ("forecast_time", "station")
    search_fields = ("station__name", "forecast_time")
    list_per_page = 100
    list_max_show_all = 100


@admin.register(WindArchiveModel)
class WindArchiveModelAdmin(admin.ModelAdmin):
    list_display = ("station", "forecast_time")
    # list_filter = ("forecast_time", "station")
    search_fields = ("station__name", "forecast_time")
    list_per_page = 100
    list_max_show_all = 100    