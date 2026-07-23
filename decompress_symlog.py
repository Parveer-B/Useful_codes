import numpy as np
import xarray as xr

def load_and_decode_dataset(filepath):
    # xarray automatically un-quantizes the int16 back to floats using scale/offset
    ds = xr.open_dataset(filepath, chunks='auto')
    
    for var in ds.data_vars:
        # Check if our custom attribute flag exists and is enabled
        if ds[var].attrs.get('is_symlog_transformed') == 1:
            
            # Reverse math: Inverse log, then scale down back to original units
            ds[var] = np.sign(ds[var]) * np.expm1(np.abs(ds[var]))
            ds[var].attrs['is_symlog_transformed'] = 0
            
            # Clean up metadata flags so your analysis scripts see clean data
            
            
    return ds