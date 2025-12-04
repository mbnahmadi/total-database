"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from .views import(
    WaveForecastView,
    WaveForecastBoundingBoxView,
    WaveArchiveView,
    WaveArchiveBoundingBoxView,
    WaveForecastView_V01,
    WaveForecastBoundingBoxView_V01,
    WaveForecastGeoJSONView
)

urlpatterns = [
    path('v1/forecast/station/', WaveForecastView_V01.as_view(), name='waveforecast_V01'),
    path('v1/forecast/bbox/', WaveForecastBoundingBoxView_V01.as_view(), name='waveforecastboundingbox_V01'),
    path('v2/wave-forecast-geojson/', WaveForecastGeoJSONView.as_view(), name='wave_forecast_geojson_V02'),


    # path('waveforecast/station/', WaveForecastView.as_view(), name='waveforecast'),
    # path('waveforecast/bbox/', WaveForecastBoundingBoxView.as_view(), name='waveforecastbbox'),
    # path('wavearchive/station/', WaveArchiveView.as_view(), name='wavearchive'),
    # path('wavearchive/bbox/', WaveArchiveBoundingBoxView.as_view(), name='wavearchivebbox'),
]
