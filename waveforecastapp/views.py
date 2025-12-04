from django.shortcuts import render
from .models import WaveStationModel, WaveForecastModel, WaveArchiveModel
from .serializers import WaveForecastSerializer, WaveArchiveSerializer, WaveStationGeoSerializer
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
from django.conf import settings



class WaveForecastView_V01(APIView):
    """
    API: Get wave forecast based on station name or location and time range.
    """

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_QUERY, description="Station name (e.g. wave_station_1)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('lat', openapi.IN_QUERY, description="Latitude (e.g. 25.5)", type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('lon', openapi.IN_QUERY, description="Longitude (e.g. 54.7)", type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start datetime (UTC)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End datetime (UTC)", type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('params', openapi.IN_QUERY, description="Comma-separated list of parameters (e.g. hs,tp,wave_direction)", type=openapi.TYPE_STRING, required=True),
        ]
    )
    def get(self, request):
        name = request.query_params.get('name')
        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        params = request.query_params.get('params', "").split(",")

        # پیدا کردن ایستگاه
        if name:
            station = WaveStationModel.objects.filter(name=name).first()
        elif lat and lon:
            try:
                point = Point(float(lon), float(lat), srid=4326)
                station = (
                    WaveStationModel.objects
                    .annotate(distance=Distance('location', point))
                    .order_by('distance')
                    .first()
                )
            except Exception:
                return Response({"error": "Invalid coordinates"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Please provide 'name' or 'lat' and 'lon'"}, status=status.HTTP_400_BAD_REQUEST)

        if not station:
            return Response({"error": "Station not found"}, status=status.HTTP_404_NOT_FOUND)

        # فیلتر اختیاری زمان
        forecasts = WaveForecastModel.objects.filter(station=station).order_by("forecast_time")
        if start_date and end_date:
            forecasts = forecasts.filter(forecast_time__range=(start_date, end_date))

        if not forecasts.exists():
            return Response({"error": "No forecast data found"}, status=status.HTTP_404_NOT_FOUND)

        # ساخت خروجی
        times = [f.forecast_time.isoformat() for f in forecasts]
        data_dict = {"forecast_time": times}
        units_dict = {"forecast_time_zone": "utc"}

        available_fields = [f.name for f in WaveForecastModel._meta.fields]
        for p in params:
            p = p.strip()
            if p and p in available_fields:
                data_dict[p] = [getattr(f, p) for f in forecasts]
                if p in settings.WAVE_PARAMETER_MAP:
                    units_dict[p] = settings.WAVE_PARAMETER_MAP[p]["unit"]

        response = {
            "metadata": {"units": units_dict},
            "latitude": station.location.y,
            "longitude": station.location.x,
            "data": data_dict
        }

        return Response(response, status=status.HTTP_200_OK)
# ======================================================================

class WaveForecastBoundingBoxView_V01(APIView):
    """
    API: دریافت پیش‌بینی موج براساس محدوده مکانی (BBox) و بازه زمانی
    GET params:
      - min_lat, max_lat
      - min_lon, max_lon
      - start_date, end_date (ISO format)
    محدودیت: حداکثر اندازه محدوده = ۰.۵ درجه
    """
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('min_lat', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('max_lat', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('min_lon', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('max_lon', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, required=True),
            openapi.Parameter('start_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('end_date', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('params', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
        ]
    )
    def get(self, request):
        # --- ۱. گرفتن مختصات ---
        try:
            min_lat = float(request.query_params.get('min_lat'))
            max_lat = float(request.query_params.get('max_lat'))
            min_lon = float(request.query_params.get('min_lon'))
            max_lon = float(request.query_params.get('max_lon'))
        except (TypeError, ValueError):
            return Response({"error": "Bounding box coordinates are required and must be float."}, status=400)

        # --- ۲. بررسی اندازه محدوده ---
        if (max_lat - min_lat > 0.5) or (max_lon - min_lon > 0.5):
            return Response({"error": "Bounding box size must not exceed 0.5 degrees."}, status=400)

        # --- ۳. گرفتن پارامترهای زمانی ---
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # --- ۴. پارامترهای انتخابی ---
        requested_params = request.query_params.get('params')
        available_fields = [f.name for f in WaveForecastModel._meta.fields if f.name not in ['id', 'station', 'forecast_time']]
        if requested_params:
            selected_fields = [p.strip() for p in requested_params.split(",") if p.strip() in available_fields]
            if not selected_fields:
                return Response({"error": f"Invalid params. Available: {', '.join(available_fields)}"}, status=400)
        else:
            selected_fields = available_fields

        # --- ۵. ایستگاه‌ها ---
        bbox = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
        stations = WaveStationModel.objects.filter(location__within=bbox)
        if not stations.exists():
            return Response({"error": "No stations found in bounding box."}, status=404)

        # --- ۶. پیش‌بینی‌ها ---
        forecasts = (
            WaveForecastModel.objects.filter(station__in=stations)
            .select_related("station")
            .only("station__location", "forecast_time", *selected_fields)
            .order_by("forecast_time", "station_id")
        )

        if start_date and end_date:
            try:
                forecasts = forecasts.filter(forecast_time__range=(start_date, end_date))
            except Exception as e:
                return Response({"error": f"Invalid datetime format: {e}"}, status=400)

        if not forecasts.exists():
            return Response({"error": "No forecast data found."}, status=404)

        # --- ۷. ساخت خروجی ---
        # استخراج زمان‌ها فقط یک‌بار
        unique_times = sorted({f.forecast_time.isoformat() for f in forecasts})

        response_data = {
            "metadata": {
                "forecast_time": unique_times,
                "units": {
                    **{p: settings.WAVE_PARAMETER_MAP[p]["unit"] for p in selected_fields if p in settings.WAVE_PARAMETER_MAP},
                    "forecast_time_zone": "utc"
                }
            },
            "stations": []
        }

        # ساخت داده‌ها بر اساس ایستگاه
        stations_dict = {}
        for f in forecasts:
            st_id = f.station.id
            if st_id not in stations_dict:
                stations_dict[st_id] = {
                    "latitude": f.station.location.y,
                    "longitude": f.station.location.x,
                    **{field: [] for field in selected_fields}
                }
            for field in selected_fields:
                stations_dict[st_id][field].append(getattr(f, field))

        response_data["stations"] = list(stations_dict.values())
        return Response(response_data, status=200)
# //////////////////////////////////////////////////////////////////////////////



# ///////////////////////////// api v02 ////////////////////////////////////////

from datetime import datetime
import pytz
from django.db.models import Prefetch


class WaveForecastGeoJSONView(APIView):
    """
    API View برای ارائه GeoJSON موج برای یک زمان مشخص شده.
    مثال URL: /api/wave-forecast-geojson/?time=2025-10-14T12:00:00Z
    """
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('time', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        # 1. دریافت و اعتبارسنجی زمان از Query Parameters
        time_str = request.query_params.get('time')
        
        if not time_str:
            return Response(
                {"detail": "'time' parameter is required: ?time=YYYY-MM-DDThh:mm:ssZ"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # فرض می‌کنیم زمان ارسالی UTC است، مانند ساختار قبلی.
            # تبدیل رشته زمان به شیء datetime با منطقه زمانی
            utc_tz = pytz.timezone('UTC')
            forecast_time_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00')).astimezone(utc_tz)
        except ValueError:
            return Response(
                {"detail": "فرمت زمان نامعتبر است. از فرمت ISO 8601 استفاده کنید."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. فیلتر کردن ایستگاه‌هایی که داده‌ای برای آن زمان دارند
        # ما فقط ایستگاه‌هایی را کوئری می‌گیریم که در آن زمان خاص دارای پیش‌بینی هستند
        stations_with_data = WaveStationModel.objects.filter(
            forecast__forecast_time=forecast_time_obj
        ).prefetch_related(
            # Prefetch فقط داده‌های پیش‌بینی مربوط به زمان فیلتر شده را لود می‌کند.
            Prefetch(
                'forecast',
                queryset=WaveForecastModel.objects.filter(forecast_time=forecast_time_obj),
                to_attr='current_forecast_data' # داده‌های پیش‌بینی در این فیلد موقت ذخیره می‌شوند
            )
        ).distinct()

        # 3. سریالایز کردن داده‌ها و پاس دادن زمان به context
        serializer = WaveStationGeoSerializer(
            stations_with_data, 
            many=True, 
            context={'forecast_time': forecast_time_obj} # ارسال زمان به سریالایزر
        )
        
        # 4. ایجاد خروجی نهایی GeoJSON
        geojson_data = serializer.data
        
        final_response_data = {
            "type": "FeatureCollection",
            "metadata": {
                "units": {"hs": "m"},
                "forecast_time": forecast_time_obj.isoformat()
            },
            "features": geojson_data['features'] 
        }

        return Response(final_response_data)







# ////////////////////////////////////////////////////////////////////////////////////
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