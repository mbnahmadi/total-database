
import numpy as np
import pandas as pd
import xarray as xr
import glob
import os

#

def create_mini_dataset_fun(f):

    ds = xr.open_dataset(f)
    u10 = ds['U10'].values
    v10 = ds['V10'].values
    T2 = ds['T2'].values
    time = pd.to_datetime( ds['XTIME'].values )
    lat = ds['XLAT'].values.squeeze()
    lon = ds['XLONG'].values.squeeze()
    lon = lon[0]
    lat = lat[:,0]

    WS10 = np.sqrt(u10**2 + v10**2)
    wind_direction = (np.arctan2(-u10, -v10) * 180 / np.pi) % 360
    WG10 = WS10 * 1.3
    WS50 = WS10 * 1.1488
    WG50 = WS50 * 1.3



    ds_combined = xr.Dataset(
        {
            "u10": (["time", "lat", "lon"], u10),
            "v10": (["time", "lat", "lon"], v10),
            "T2": (["time", "lat", "lon"], T2),
            "WS10": (["time", "lat", "lon"], WS10),
            "wind_direction": (["time", "lat", "lon"], wind_direction),
            "WG10": (["time", "lat", "lon"], WG10),
            "WS50": (["time", "lat", "lon"], WS50),
            "WG50": (["time", "lat", "lon"], WG50),
        },
        coords={
            "time": time,
            "lat": lat,
            "lon": lon
        }
    )

    return ds_combined


data_fol = 'C:/Users/luffy/Desktop/presentation/New folder (46)/'
files = glob.glob(os.path.join(data_fol, "*.mean.nc"))
#
c1=[]
for f in files:

    ds= create_mini_dataset_fun(f)
    c1.append(ds)

ds_overal = xr.concat(c1,dim='time')
try:
    ds_overal.to_netcdf('merged_nc_file.nc')
except Exception as e:
    print(e)
    # print('file already exists')



