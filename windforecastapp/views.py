from django.shortcuts import render
from .models import WindArchiveModel, WindStationModel, WindForecastModel
from .serializers import WindForecastSerializer, WindArchiveSerializer
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
class WindForecastView(APIView):
    '''
    API: get wind forecast based on station name or location (lat/lon) and forecast_time.
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
                station = WindStationModel.objects.get(name=name)
            except WindStationModel.DoesNotExist:
                return Response({"error": "Station not found by name"}, status=status.HTTP_404_NOT_FOUND)

        elif lat and lon:
            try:
                point = Point(float(lon), float(lat), srid=4326)   
                station = (
                    WindStationModel.objects.annotate(distance=Distance('location', point))
                    .order_by('distance')
                    .first()
                ) 
            except Exception:
                return Response({"error": "Invalid coordinates"}, status=status.HTTP_400_BAD_REQUEST)
        else:
             return Response({"error": "Please provide 'name' or 'lat' and 'lon'"}, status=status.HTTP_400_BAD_REQUEST)

        forecasts = WindForecastModel.objects.filter(station=station)

        if start_date and end_date:
            try:
                # start_dt = make_aware(parse_datetime(start_date))
                # end_dt = make_aware(parse_datetime(end_date))
                forecasts = forecasts.filter(forecast_time__range=(start_date, end_date))
            except Exception as e:
                return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WindForecastSerializer(forecasts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WindForecastBoundingBoxView(APIView):
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
    
    


    # def get(self, request):
    #     try:
    #         min_lat = float(request.query_params.get('min_lat'))
    #         max_lat = float(request.query_params.get('max_lat'))
    #         min_lon = float(request.query_params.get('min_lon'))
    #         max_lon = float(request.query_params.get('max_lon'))
    #     except (TypeError, ValueError):
    #         return Response({"error": "Latitude and longitude range are required and must be float."}, status=400)

    #     # delta_lat = max_lat - min_lat
    #     # delta_lon = max_lon - min_lon

    #     # if delta_lat > 0.5 or delta_lon > 0.5:
    #     #     return Response({
    #     #         "error": "Bounding box is too large. Please keep the area smaller than 0.5 degrees in lat/lon."
    #     #     }, status=400)

    #     try:
    #         start = request.query_params.get('start_date')
    #         end = request.query_params.get('end_date')
    #     except Exception as e:
    #         return Response({"error": f"{e}"}, status=400)

    #     stations = WindStationModel.objects.filter(
    #         location__y__gte=min_lat,
    #         location__y__lte=max_lat,
    #         location__x__gte=min_lon,
    #         location__x__lte=max_lon,
    #     )

    #     if not stations.exists():
    #         return Response({"error": "No stations found in bounding box."}, status=404)

    #     forecasts = WindForecastModel.objects.filter(
    #         station__in=stations,
    #         forecast_time__range=(start, end)
    #     ).select_related('station')

    #     if not forecasts.exists():
    #         return Response({"error": "No forecast data found in time and location range."}, status=404)

    #     serializer = WindForecastSerializer(forecasts, many=True)
    #     return Response(serializer.data, status=200)

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
    
        stations = WindStationModel.objects.filter(location__within=bbox)

        print(f"start: {start_date}, end: {end_date}")
        print(f"min lat: {min_lat}, max lat: {max_lat}, min lon: {min_lon}, max lon: {max_lon}")
        print(f"min: {WindForecastModel.objects.order_by('forecast_time').first().forecast_time}")
        print(f"max: {WindForecastModel.objects.order_by('-forecast_time').first().forecast_time}")

        if not stations.exists():
            return Response({"error": "No stations found in bounding box."}, status=404)

        # print(stations)

        forecasts = WindForecastModel.objects.filter(
            station__in=stations,
            forecast_time__range=(start_date, end_date)
        ).select_related('station').order_by('station_id', 'forecast_time')
        # print('forecasts',forecasts)

        if not forecasts.exists():
            return Response({"error": "No forecast data found in time and location range."}, status=404)

        serializer = WindForecastSerializer(forecasts, many=True)
        return Response(serializer.data, status=200)
###########################    ARCHIVE VIEW     ####################################

class WindArchiveView(APIView):
    '''
    API: get wind Archive based on station name or location (lat/lon) and forecast_time.
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
                station = WindStationModel.objects.get(name=name)
            except WindStationModel.DoesNotExist:
                return Response({"error": "Station not found by name"}, status=status.HTTP_404_NOT_FOUND)

        elif lat and lon:
            try:
                point = Point(float(lon), float(lat), srid=4326)   
                station = (
                    WindStationModel.objects.annotate(distance=Distance('location', point))
                    .order_by('distance')
                    .first()
                ) 
            except Exception:
                return Response({"error": "Invalid coordinates"}, status=status.HTTP_400_BAD_REQUEST)
        else:
             return Response({"error": "Please provide 'name' or 'lat' and 'lon'"}, status=status.HTTP_400_BAD_REQUEST)

        forecasts = WindForecastModel.objects.filter(station=station)

        if start_date and end_date:
            try:
                # start_dt = make_aware(parse_datetime(start_date))
                # end_dt = make_aware(parse_datetime(end_date))
                forecasts = forecasts.filter(forecast_time__range=(start_date, end_date))
            except Exception as e:
                return Response({"error": f"{e}"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = WindArchiveSerializer(forecasts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WindArchiveBoundingBoxView(APIView):
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
    
        stations = WindStationModel.objects.filter(location__within=bbox)

        print(f"start: {start_date}, end: {end_date}")
        print(f"min lat: {min_lat}, max lat: {max_lat}, min lon: {min_lon}, max lon: {max_lon}")
        print(f"min: {WindArchiveModel.objects.order_by('forecast_time').first().forecast_time}")
        print(f"max: {WindArchiveModel.objects.order_by('-forecast_time').first().forecast_time}")

        if not stations.exists():
            return Response({"error": "No stations found in bounding box."}, status=404)

        # print(stations)

        forecasts = WindArchiveModel.objects.filter(
            station__in=stations,
            forecast_time__range=(start_date, end_date)
        ).select_related('station').order_by('station_id', 'forecast_time')
        # print('forecasts',forecasts)

        if not forecasts.exists():
            return Response({"error": "No forecast data found in time and location range."}, status=404)

        serializer = WindForecastSerializer(forecasts, many=True)
        return Response(serializer.data, status=200)




# class WindForecastLatLonView(APIView):
#     @swagger_auto_schema(
#         manual_parameters=[
#             openapi.Parameter('lat', openapi.IN_QUERY, description="Latitude (e.g. 24.56)", type=openapi.TYPE_NUMBER, required=True),
#             openapi.Parameter('lon', openapi.IN_QUERY, description="Longitude (e.g. 54.78)", type=openapi.TYPE_NUMBER, required=True),
#             openapi.Parameter('startdate', openapi.IN_QUERY, description="Start datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
#             openapi.Parameter('enddate', openapi.IN_QUERY, description="End datetime (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING, required=True),
#         ],
#         responses={
#             200: openapi.Response(description="List of weather forecasts near the given point."),
#             400: "Invalid input parameters.",
#         }
#     )
#     def get(self, request):
#         # --- Step 1: Validate inputs ---
#         lat = request.query_params.get('lat')
#         lon = request.query_params.get('lon')
#         startdate = request.query_params.get('startdate')
#         enddate = request.query_params.get('enddate')

#         try:
#             lat = float(lat)
#             lon = float(lon)
#             if not (-90 <= lat <= 90 and -180 <= lon <= 180):
#                 raise ValidationError("Latitude must be between -90 and 90, and longitude between -180 and 180.")

#             startdate = datetime.strptime(startdate, '%Y-%m-%dT%H:%M:%S')
#             enddate = datetime.strptime(enddate, '%Y-%m-%dT%H:%M:%S')
#             if startdate >= enddate:
#                 raise ValidationError("Start date must be earlier than end date.")

#         except (TypeError, ValueError):
#             raise ValidationError("Invalid query parameters. Please check the format.")

#         # --- Step 2: Build geospatial query ---
#         user_point = Point(lon, lat)  # Point(longitude, latitude)
#         radius_km = 10  # You can change this if needed

#         forecasts = WindForecastModel.objects.filter(
#             forecast_time__range=(startdate, enddate),
#             station__location__distance_lte=(user_point, D(km=radius_km))
#         ).annotate(
#             distance=Distance('station__location', user_point)
#         ).order_by('forecast_time')

#         # --- Step 3: Serialize response ---
#         serializer = WindForecastSerializer(forecasts, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)
    



# class WindForecastStationNameView(APIView):
#     @swagger_auto_schema(
#         manual_parameters=[
#             openapi.Parameter('station_name', openapi.IN_QUERY, description="station name", type=openapi.TYPE_STRING, required=True),
#             openapi.Parameter('startdate', openapi.IN_QUERY, description="start date format: YYYY-MM-DDTHH:MM:SS", type=openapi.TYPE_STRING, required=True),
#             openapi.Parameter('enddate', openapi.IN_QUERY, description="end date format: YYYY-MM-DDTHH:MM:SS", type=openapi.TYPE_STRING, required=True),
#         ],
#         responses={
#             200: openapi.Response(
#                 description="Weather information returned successfully.",
#             ),
#             400: "Passed parameters are not valid.",
#         })
#     def get(self, request):
#         station_name = request.query_params.get('station_name')
#         startdate = request.query_params.get('startdate')
#         enddate = request.query_params.get('enddate')
#         if startdate and enddate:
#             startdate = datetime.strptime(startdate, '%Y-%m-%dT%H:%M:%S')
#             enddate = datetime.strptime(enddate, '%Y-%m-%dT%H:%M:%S')
#             forecasts = WindForecastModel.objects.filter(forecast_time__range=(startdate, enddate), station__name=station_name)
#         else:
#             forecasts = WindForecastModel.objects.all()
#         serializer = WindForecastSerializer(forecasts, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

# # class WindForecastBoundingBoxView(APIView):
# #     def get(self, request):
# #         min_lat = request.query_params.get('min_lat')
# #         min_lon = request.query_params.get('min_lon')
# #         max_lat = request.query_params.get('max_lat')