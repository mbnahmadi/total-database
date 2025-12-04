from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelListSerializer, GeoFeatureModelSerializer
from .models import WaveStationModel, WaveForecastModel, WaveArchiveModel


class WaveArchiveDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaveStationModel
        exclude = ['station']

class WaveForecastSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)# چون در این فیلد ما کلید خارجی داریم و فیلد با نام station هست پس میگیم از station فقط name رو نمایش بده
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = WaveForecastModel
        fields = [
            'station_name',
            'latitude',
            'longitude',
            'forecast_time', 
            'tp','hs','hmax','tz','wave_direction'
        ]
        
    def get_latitude(self, obj):
        return obj.station.location.y

    def get_longitude(self, obj):
        return obj.station.location.x

class WaveArchiveSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)# چون در این فیلد ما کلید خارجی داریم و فیلد با نام station هست پس میگیم از station فقط name رو نمایش بده
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = WaveArchiveModel
        fields = [
            'station_name',
            'latitude',
            'longitude',
            'forecast_time', 
            'tp','hs','hmax','tz','wave_direction'
        ]
        
    def get_latitude(self, obj):
        return obj.station.location.y

    def get_longitude(self, obj):
        return obj.station.location.x




# class WindArchiveSerializer(serializers.ModelSerializer):
#     station_name = serializers.CharField(source='station.name', read_only=True)# چون در این فیلد ما کلید خارجی داریم و فیلد با نام station هست پس میگیم از station فقط name رو نمایش بده
#     latitude = serializers.SerializerMethodField()
#     longitude = serializers.SerializerMethodField()

#     class Meta:
#         model = WindArchiveModel
#         fields = [
#             'station_name',
#             'latitude',
#             'longitude',
#             'forecast_time',
#             'T2', 'U10', 'V10', 'Q2', 'RAINNC', 'PSFC'
#         ]
        
#     def get_latitude(self, obj):
#         return obj.station.location.y

#     def get_longitude(self, obj):
#         return obj.station.location.x


# ===============================================================================

class WaveForecastDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaveForecastModel
        fields = ['forecast_time', 'hs']

# 2. سریالایزر اصلی برای تولید GeoJSON
class WaveStationGeoSerializer(GeoFeatureModelSerializer):
    # مقدار hs مربوط به زمان فیلتر شده (نه آرایه)
    current_hs = serializers.SerializerMethodField()
    
    class Meta:
        model = WaveStationModel
        geo_field = "location"
        # فقط فیلدهای مورد نیاز و فیلد hs فعلی
        fields = ('name', 'current_hs')

    def get_current_hs(self, obj):
        """
        استخراج مقدار Hs از داده‌هایی که قبلاً (با Prefetch) لود شده‌اند.
        """
        # 'current_forecast_data' نام فیلدی است که در Prefetch تعیین کردیم
        if hasattr(obj, 'current_forecast_data') and obj.current_forecast_data:
            # چون ما مطمئن هستیم که فقط یک مقدار در آن زمان وجود دارد:
            return obj.current_forecast_data[0].hs
        return None
    