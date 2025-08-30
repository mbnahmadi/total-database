import xarray as xr

ds = xr.open_dataset('F:\\merged_gfs.2025070200.nc')

print(ds.time_str.values)