from django.shortcuts import render
from .models import WaveStationModel, WaveForecastModel, WaveArchiveModel
from .serializers import WaveForecastSerializer, WaveArchiveSerializer
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.geos import Polygon


# Create your views here.
class WaveForecastView(APIView):
    '''
    API: get wave forecast based on station name or location (lat/lon) and forecast_time.
    '''
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_QUERY, description="Station Name (e.g. Station_0)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('lat', openapi.IN_QUERY, description="Latitude (e.g. 24.56)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('lon', openapi.IN_QUERY, description="Longitude (e.g. 54.78)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('startdate', openapi.IN_QUERY, description="Start datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('enddate', openapi.IN_QUERY, description="End datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
    ])

    def get(self, request):
        name = request.query_params.get('name')
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        start_date = request.query_params.get('startdate')
        end_date = request.query_params.get('enddate')

        station = None

        if name:
            try:
                station = WaveStationModel.objects.get(name=name)
            except WaveStationModel.DoesNotExist:
                return Response({"error": "Station not found by name"}, status=status.HTTP_404_NOT_FOUND)

        elif lat and lon:
            try:
                point = Point(float(lon), float(lat), srid=4326)   
                station = (
                    WaveStationModel.objects.annotate(distance=Distance('location', point))
                    .order_by('distance')
                    .first()
                ) 
            except Exception:
                return Response({"error": "Invalid coordinates"}, status=status.HTTP_400_BAD_REQUEST)
        else:
             return Response({"error": "Please provide 'name' or 'lat' and 'lon'"}, status=status.HTTP_400_BAD_REQUEST)

        forecasts = WaveForecastModel.objects.filter(station=station)

        if start_date and end_date:
            try:
                # start_dt = make_aware(parse_datetime(start_date))
                # end_dt = make_aware(parse_datetime(end_date))
                forecasts = forecasts.filter(forecast_time__range=(start_date, end_date))
            except Exception as e:
                return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WaveForecastSerializer(forecasts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WaveForecastBoundingBoxView(APIView):
    """
    API: دریافت پیش‌بینی باد براساس محدوده مکانی (BBox) و بازه زمانی
    GET params:
      - min_lat, max_lat
      - min_lon, max_lon
      - start_date, end_date (ISO format)
    محدودیت: حداکثر اندازه محدوده = ۰.۵ درجه
    """
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('min_lat', openapi.IN_QUERY, description="Minimum Latitude (e.g. 24.56)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('max_lat', openapi.IN_QUERY, description="Maximum Latitude (e.g. 25.87)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('min_lon', openapi.IN_QUERY, description="Minimum Longitude (e.g. 70.02)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('max_lon', openapi.IN_QUERY, description="Maximum Longitude (e.g. 71.78)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
    ],
    responses={
            400 : 'The size of the Boundin box should not be more than 0.5 degrees.'
        }
    )

    def get(self, request):
        try:
            min_lat = float(request.query_params.get('min_lat'))
            max_lat = float(request.query_params.get('max_lat'))
            min_lon = float(request.query_params.get('min_lon'))
            max_lon = float(request.query_params.get('max_lon'))
        except (TypeError, ValueError):
            return Response({"error": "Latitude and longitude range are required and must be float."}, status=400)

        try:
            start_date = (request.query_params.get('start_date'))
            end_date = (request.query_params.get('end_date'))
        except Exception as e:
            return Response({"error": f"{e}"}, status=400)

        # ساختن محدوده مکانی به صورت Polygon
        bbox = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
    
        stations = WaveStationModel.objects.filter(location__within=bbox)

        # print(f"start: {start_date}, end: {end_date}")
        # print(f"min lat: {min_lat}, max lat: {max_lat}, min lon: {min_lon}, max lon: {max_lon}")
        # print(f"min: {WaveArchiveModel.objects.order_by('forecast_time').first().forecast_time}")
        # print(f"max: {WaveArchiveModel.objects.order_by('-forecast_time').first().forecast_time}")

        if not stations.exists():
            return Response({"error": "No stations found in bounding box."}, status=404)

        # print(stations)

        forecasts = WaveForecastModel.objects.filter(
            station__in=stations,
            forecast_time__range=(start_date, end_date)
        ).select_related('station').order_by('station_id', 'forecast_time')
        # print('forecasts',forecasts)

        if not forecasts.exists():
            return Response({"error": "No forecast data found in time and location range."}, status=404)

        serializer = WaveForecastSerializer(forecasts, many=True)
        return Response(serializer.data, status=200)

#------------------------------
# Wave Archive API
#------------------------------

class WaveArchiveView(APIView):
    '''
    API: get wave Archive based on station name or location (lat/lon) and forecast_time.
    '''
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_QUERY, description="Station Name (e.g. Station_0)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('lat', openapi.IN_QUERY, description="Latitude (e.g. 24.56)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('lon', openapi.IN_QUERY, description="Longitude (e.g. 54.78)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('startdate', openapi.IN_QUERY, description="Start datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('enddate', openapi.IN_QUERY, description="End datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
    ])

    def get(self, request):
        name = request.query_params.get('name')
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        start_date = request.query_params.get('startdate')
        end_date = request.query_params.get('enddate')

        station = None

        if name:
            try:
                station = WaveStationModel.objects.get(name=name)
            except WaveStationModel.DoesNotExist:
                return Response({"error": "Station not found by name"}, status=status.HTTP_404_NOT_FOUND)

        elif lat and lon:
            try:
                point = Point(float(lon), float(lat), srid=4326)   
                station = (
                    WaveStationModel.objects.annotate(distance=Distance('location', point))
                    .order_by('distance')
                    .first()
                ) 
            except Exception:
                return Response({"error": "Invalid coordinates"}, status=status.HTTP_400_BAD_REQUEST)
        else:
             return Response({"error": "Please provide 'name' or 'lat' and 'lon'"}, status=status.HTTP_400_BAD_REQUEST)

        forecasts = WaveArchiveModel.objects.filter(station=station)

        if start_date and end_date:
            try:
                # start_dt = make_aware(parse_datetime(start_date))
                # end_dt = make_aware(parse_datetime(end_date))
                forecasts = forecasts.filter(forecast_time__range=(start_date, end_date))
            except Exception as e:
                return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WaveArchiveSerializer(forecasts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WaveArchiveBoundingBoxView(APIView):
    """
    API: دریافت پیش‌بینی باد براساس محدوده مکانی (BBox) و بازه زمانی
    GET params:
      - min_lat, max_lat
      - min_lon, max_lon
      - start_date, end_date (ISO format)
    محدودیت: حداکثر اندازه محدوده = ۰.۵ درجه
    """
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('min_lat', openapi.IN_QUERY, description="Minimum Latitude (e.g. 24.56)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('max_lat', openapi.IN_QUERY, description="Maximum Latitude (e.g. 25.87)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('min_lon', openapi.IN_QUERY, description="Minimum Longitude (e.g. 70.02)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('max_lon', openapi.IN_QUERY, description="Maximum Longitude (e.g. 71.78)", type=openapi.TYPE_NUMBER, required=False),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
    ],
    responses={
            400 : 'The size of the Boundin box should not be more than 0.5 degrees.'
        }
    )

    def get(self, request):
        try:
            min_lat = float(request.query_params.get('min_lat'))
            max_lat = float(request.query_params.get('max_lat'))
            min_lon = float(request.query_params.get('min_lon'))
            max_lon = float(request.query_params.get('max_lon'))
        except (TypeError, ValueError):
            return Response({"error": "Latitude and longitude range are required and must be float."}, status=400)

        try:
            start_date = (request.query_params.get('start_date'))
            end_date = (request.query_params.get('end_date'))
        except Exception as e:
            return Response({"error": f"{e}"}, status=400)

        # ساختن محدوده مکانی به صورت Polygon
        bbox = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
    
        stations = WaveStationModel.objects.filter(location__within=bbox)

        print(f"start: {start_date}, end: {end_date}")
        print(f"min lat: {min_lat}, max lat: {max_lat}, min lon: {min_lon}, max lon: {max_lon}")
        print(f"min: {WaveArchiveModel.objects.order_by('forecast_time').first().forecast_time}")
        print(f"max: {WaveArchiveModel.objects.order_by('-forecast_time').first().forecast_time}")

        if not stations.exists():
            return Response({"error": "No stations found in bounding box."}, status=404)

        # print(stations)

        forecasts = WaveArchiveModel.objects.filter(
            station__in=stations,
            forecast_time__range=(start_date, end_date)
        ).select_related('station').order_by('station_id', 'forecast_time')
        # print('forecasts',forecasts)

        if not forecasts.exists():
            return Response({"error": "No forecast data found in time and location range."}, status=404)

        serializer = WaveArchiveSerializer(forecasts, many=True)
        return Response(serializer.data, status=200)