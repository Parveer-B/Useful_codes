def compress_zfp(file_info, precision = 8):
    infl, outfl = file_info
    ds = xr.open_dataset(infl)
    compressed_package = {
        "metadata": {
            "dims": dict(ds.dims),
            "attrs": ds.attrs,
            "variables_meta": {},
        },
        "data_blobs": {},
    }
    for coord_name in ds.coords:
        coord_data = ds.coords[coord_name]
        compressed_package["metadata"]["variables_meta"][coord_name] = {
            "dims": coord_data.dims,
            "attrs": coord_data.attrs,
            "dtype": str(coord_data.dtype),
            "shape": coord_data.shape,
        }
        # Load coordinate array directly
        compressed_package["data_blobs"][coord_name] = coord_data.values
    for var_name in ds.data_vars:

        var_data = ds[var_name]
    
        # Save variable-specific coordinate names and attributes
        compressed_package["metadata"]["variables_meta"][var_name] = {
            "dims": var_data.dims,
            "attrs": var_data.attrs,
            "dtype": str(var_data.dtype),
            "shape": var_data.shape,
        }
        arr = var_data.compute().values
        if arr.dtype.kind in ["f", "i"] and arr.ndim > 0:
            print(f"Compressing [{var_name}] with shape {arr.shape} using zfpy...")
            compressed_bytes = zfpy.compress_numpy(arr, precision = precision)
    
            compressed_package["data_blobs"][var_name] = compressed_bytes
        else:
            print(f"Storing [{var_name}] uncompressed (coordinate/string/scalar)...")
            compressed_package["data_blobs"][var_name] = arr
    del arr
    del var_data
    gc.collect()

    #write to disk
    output_file = outfl
    with open(output_file, "wb") as f:
        pickle.dump(compressed_package, f, protocol=pickle.HIGHEST_PROTOCOL)
    
def decompress_zfp(file):
    with open(file, "rb") as f:
        package = pickle.load(f)

    meta = package["metadata"]
    blobs = package["data_blobs"]
    reconstructed_vars = {}
    
    # 2. Iterate and unpack variables
    for var_name, var_meta in meta["variables_meta"].items():
        raw_blob = blobs[var_name]
    
        if isinstance(raw_blob, bytes):
            # This was compressed using zfpy
            decompressed_arr = zfpy.decompress_numpy(raw_blob)
        else:
            # This was an uncompressed metadata element
            decompressed_arr = raw_blob
    
        # Re-wrap back into an Xarray DataArray with original names and properties
        reconstructed_vars[var_name] = xr.DataArray(
            data=decompressed_arr,
            dims=var_meta["dims"],
            attrs=var_meta["attrs"],
            name=var_name,
    )
    #put the data arrays back into a new dataset
    new_ds = xr.Dataset(
        data_vars={
            k: v for k, v in reconstructed_vars.items() if k not in meta["dims"]
        },
        coords={k: reconstructed_vars[k] for k in meta["dims"] if k in reconstructed_vars},
        attrs=meta["attrs"],
    )
    return new_ds
    