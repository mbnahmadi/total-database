from django.contrib.gis.db.models.fields import RasterField
from django.db import models
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.db import models
from django.db import connection

class RasterLayerModel(models.Model):
    time = models.DateTimeField()
    param = models.CharField(max_length=50) # e.g. ws10
    rast = RasterField(srid=4326)
    