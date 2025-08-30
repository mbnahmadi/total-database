from django import forms
from .models import WindStationModel
from django.contrib.gis.geos import Point


# class WindStationForm(forms.ModelForm):
#     latitude = forms.FloatField(required=False)
#     longitude = forms.FloatField(required=False)
    
#     class Meta:
#         model = WindStationModel
#         fields = ("name", "location", "latitude", "longitude")

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if self.instance and self.instance.location:
#             self.fields['latitude'].initial = self.instance.location.y
#             self.fields['longitude'].initial = self.instance.location.x

#     def save(self, commit=True):
#         instance = super().save(commit=False) #ابجکت ساخته میشه ولی ذخیره نمیشه در دیتابیس
#         lon = self.cleaned_data.get('longitude')
#         lat = self.cleaned_data.get('latitude')
#         if lon is not None and lat is not None:
#             instance.location = Point(lon, lat)
#         if commit:
#             instance.save()
#         return instance