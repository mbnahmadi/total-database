from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import WindStationModel, WindForecastModel, WindArchiveModel


class WindForecastSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)# چون در این فیلد ما کلید خارجی داریم و فیلد با نام station هست پس میگیم از station فقط name رو نمایش بده
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = WindForecastModel
        fields = [
            'id',
            'station_name',
            'latitude',
            'longitude',
            'forecast_time',
            'temperature', 'ws10', 'wind_direction',
            'wg10', 'ws50', 'wg50'

        ]
        
    def get_latitude(self, obj):
        return obj.station.location.y

    def get_longitude(self, obj):
        return obj.station.location.x


class WindArchiveSerializer(serializers.ModelSerializer):
    station_name = serializers.CharField(source='station.name', read_only=True)# چون در این فیلد ما کلید خارجی داریم و فیلد با نام station هست پس میگیم از station فقط name رو نمایش بده
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    # point = serializers.SerializerMethodField()

    class Meta:
        model = WindArchiveModel
        fields = [
            'id',
            'station_name',
            'latitude',
            'longitude',
            'forecast_time',
            'temperature', 'ws10', 'wind_direction',
            'wg10', 'ws50', 'wg50'
        ]

    def get_latitude(self, obj):
        return obj.station.location.y

    def get_longitude(self, obj):
        return obj.station.location.x
        

    # def get_point(self, obj):
    #     return {
    #         "lat": obj.station.location.y,
    #         "lon": obj.station.location.x
    #     }

