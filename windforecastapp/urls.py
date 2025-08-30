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
from .views import (
    WindForecastView, 
    WindForecastBoundingBoxView,
    WindArchiveView,
    WindArchiveBoundingBoxView
    )

urlpatterns = [
    path('windforecast/station/', WindForecastView.as_view(), name='windforecast'),
    path('windforecast/bbox/', WindForecastBoundingBoxView.as_view(), name='windforecastbbox'),
    path('windarchive/station/', WindArchiveView.as_view(), name='windarchive'),
    path('windarchive/bbox/', WindArchiveBoundingBoxView.as_view(), name='windarchivebbox'),
]
