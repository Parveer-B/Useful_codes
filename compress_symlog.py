import mpi4py
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import time
import gc
import matplotlib.colors as colors
import concurrent.futures
from functools import partial
import multiprocessing
import netCDF4
import tracemalloc
import warnings
import os
from xarray.coding.times import SerializationWarning


def lossy_compression_algo(infl, outfl, scalefac=65535, vertchunks = 1, complev=4, numvert = 300):

    #supress xarray warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="xarray")
    warnings.filterwarnings("ignore", category=SerializationWarning)
    
    # SUPPRESS HDF5 C-LIBRARY INTERNAL DIAGNOSTIC LOGS
    # This prevents the HDF5-DIAG output from printing to your notebook terminal
    os.environ["HDF5_DISABLE_VERSION_CHECK"] = "1"
    #with xr.open_dataset(infl, chunks='auto', cache=False) as ds:
    vertchunk_size = numvert // vertchunks
    with xr.open_dataset(infl, chunks = {"lev": vertchunk_size}, cache=False) as ds:
        encoding = {}
        fvalue = -32768
        deletevars = ["nci", "ncs", "ncr", "ncg", "qg", "qc", "qr", "qs", "lenscl"] #variables do delete!
        vars_to_drop = [v for v in ds.data_vars if v.lower() in deletevars]
        ds = ds.drop_vars(vars_to_drop)
        # We process variable-by-variable so Dask only loads one data track at a time
        for var in ds.data_vars:
            if var.lower() in deletevars:
                ds = ds.drop_vars(var)
            
            # Apply Symlog transform lazily (No computation happens yet)
            # This protects your near-zero relative errors
            if "pert" in var.lower() or "tke" in var.lower() or "dissten" in var.lower() or var.lower()[0] == "q":
                if var.lower()[0] == "q":
                    scaled_var = ds[var] * 1607800
                    transformed_var = np.sign(scaled_var) * np.log1p(np.abs(scaled_var))
                    transformed_var.attrs['units'] = '(ppmv)'
                else:
                    transformed_var = np.sign(ds[var]) * np.log1p(np.abs(ds[var]))
                transformed_var.attrs['is_symlog_transformed'] = 1
                ds[var] = transformed_var

            else:
                # Don't transform
                ds[var].attrs['is_symlog_transformed'] = 0
                
                # Compute min/max for ONLY this specific variable to protect RAM
                # Using .values pulls only the final 2 scalar numbers into memory
            var_min = float(ds[var].min().values)
            var_max = float(ds[var].max().values)
                # Update the dataset inline with the transformed log-space data
                
            
            
            
            # Calculate standard NetCDF scale/offset linearly on the LOG space
            if var_max - var_min == 0:
                scale = 1e-6
                offset = var_min
            else:
                scale = (var_max - var_min) / (scalefac - 2)
                offset = var_min + (scale * (scalefac / 2))
            if scale <= 1e-6:
                scale = 1e-6
            
            
            # Construct quantization mapping for int16 + zlib compression
            encoding[var] = {
                '_FillValue': fvalue,
                'scale_factor': scale,
                'add_offset': offset,
                'dtype': 'int16',
                'zlib': True,
                'complevel': complev
            }
            
        # 2. Stream directly to disk. 
        # xarray reads a chunk, logs it, converts to int16, and writes it immediately.
        ds.to_netcdf(outfl, encoding=encoding)
        print(f"{outfl} written to disk")
    # Explicitly clear out object references and clean RAM
    del ds
    gc.collect()
   
def compress_data(vertlevs, exp, timesteps):
    # CRITICAL: NetCDF/HDF5 libraries are not fork-safe. 
    # Force 'spawn' to prevent random deadlocks or crashes in parallel.
    # multiprocessing.set_start_method('spawn', force=True)
    os.environ["HDF5_DISABLE_VERSION_CHECK"] = "1"
    # Configuration
    complev = 4
    vertchunks = 6
    types = ["s" , "w"]
    scale = 16384
    
    # Create the queue using lightweight string paths instead of loaded datasets
    tasks = []
    for typee in types:
        for tstep in timesteps: 
            infl = f"cm1out_{str(tstep).zfill(6)}_{typee}.nc" 
            #ADJUST BELOW
            outfl = f"exp{exp}_lossy_symlog_{str(tstep).zfill(6)}{typee}_clev{complev}_scale{scale}.nc"
            tasks.append((infl, outfl))

    # Change processes=1 to processes=4 to run 4 files simultaneously
    start_time = time.time()
    tracemalloc.start()
    print("starting file generation")
    with multiprocessing.Pool(processes=8, maxtasksperchild=1) as pool:
        # FIX: Your task tuple is (infl, outfl). 
        # For starmap to unpack it correctly, construct the arguments as (infl, outfl, 65535, 1, complev)
        # to match your function signature: lossy_compression_algo(infl, outfl, scalefac, vertchunks, complev)
        starmap_args = [(infl, outfl, scale, vertchunks, complev, vertlevs) for infl, outfl in tasks]
        
        results = pool.starmap(lossy_compression_algo, starmap_args)
    end_time = time.time()
    timetods = end_time - start_time
    print(f"Took {timetods}s to make the files")
    curram, peakram = tracemalloc.get_traced_memory()
    peakram /= (10**9)
    print(f"total .nc creation time is {timetods:.4f} seconds with max RAM of {peakram:.2f} GB")
    tracemalloc.stop()
    
if __name__ == '__main__':
    import sys
    
    # Check if the user provided the correct number of arguments
    if len(sys.argv) < 3:
        print("Usage: python compress_symlog.py <vertlevs> <timestep1> <timestep2> ...")
        sys.exit(1)
        
    # First argument is the number of vertical levels (integer)
    vertlevs = int(sys.argv[1])
    exp = int(sys.argv[2])
    
    # Remaining arguments are the timesteps (integers)
    timesteps = [int(t) for t in sys.argv[3:]]
    
    # Run your function
    compress_data(vertlevs, exp, timesteps)   