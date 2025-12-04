import numpy as np
import pandas as pd
import xarray as xr
import glob, os

def create_mini_dataset_fun(f):
    ds = xr.open_dataset(f)

    # اگر بعد record وجود دارد، اولین مقدارش را انتخاب کن
    if "record" in ds.dims:
        ds = ds.isel(record=0)

    # استخراج متغیرها
    u10 = ds['U10'].squeeze().values  # شکل: (Time, south_north, west_east)
    v10 = ds['V10'].squeeze().values
    T2  = ds['T2'].squeeze().values


    # تبدیل time
    time = pd.to_datetime(ds['XTIME'].values)
    if time.ndim == 0:  # اگر فقط یک لحظه است
        time = [time]

    # lat, lon → (south_north, west_east)
    lat = ds['XLAT'].squeeze().values
    lon = ds['XLONG'].squeeze().values

    # به بردار 1بعدی تبدیل کن
    lat_1d = lat[:, 0]
    lon_1d = lon[0, :]

    # محاسبه سرعت و جهت باد
    WS10 = np.sqrt(u10**2 + v10**2)
    wind_direction = (np.arctan2(-u10, -v10) * 180 / np.pi) % 360
    WG10 = WS10 * 1.3
    WS50 = WS10 * 1.1488
    WG50 = WS50 * 1.3


    # ابعاد داده‌ها را بررسی کن
    # print(f"Shape u10: {u10.shape}, time: {len(time)}, lat: {len(lat_1d)}, lon: {len(lon_1d)}")

    # اگر فقط یک مقدار در بعد time است، reshape کن تا 3بعدی شود
    if u10.ndim == 2:
        u10 = u10[np.newaxis, :, :]
        v10 = v10[np.newaxis, :, :]
        T2 = T2[np.newaxis, :, :]
        WS10 = WS10[np.newaxis, :, :]
        wind_direction = wind_direction[np.newaxis, :, :]
        WG10 = WG10[np.newaxis, :, :]
        WS50 = WS50[np.newaxis, :, :]
        WG50 = WG50[np.newaxis, :, :]


    # ساخت Dataset نهایی
    ds_combined = xr.Dataset(
        {
            "u10": (["time", "lat", "lon"], u10),
            "v10": (["time", "lat", "lon"], v10),
            "T2":  (["time", "lat", "lon"], T2),
            "WS10": (["time", "lat", "lon"], WS10),
            "wind_direction": (["time", "lat", "lon"], wind_direction),
            "WG10": (["time", "lat", "lon"], WG10),
            "WS50": (["time", "lat", "lon"], WS50),
            "WG50": (["time", "lat", "lon"], WG50),

        },
        coords={
            "time": time,
            "lat": lat_1d,
            "lon": lon_1d,
        }
    )

    return ds_combined


data_fol = '/home/OUTPUT/OR_Website_Data/PersianGulf/WindData/2025101412'
files = glob.glob(os.path.join(data_fol, "*.nc"))

datasets = []
for f in files:
    print(f"\nProcessing {f}")
    ds = create_mini_dataset_fun(f)
    datasets.append(ds)

ds_overal = xr.concat(datasets, dim='time')

try:
    ds_overal.to_netcdf('merged_nc_file.nc')
    print("Merge complete and saved as merged_nc_file.nc")
except Exception as e:
    print("Error:", e)
