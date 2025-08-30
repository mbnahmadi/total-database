from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
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
