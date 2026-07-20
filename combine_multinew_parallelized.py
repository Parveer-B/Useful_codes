import os
import glob
import numpy as np
import xarray as xr
import sys #lets us pass arguments
import netCDF4 as nc
import time
from concurrent.futures import ProcessPoolExecutor

#https://www.geeksforgeeks.org/python/pass-list-as-command-line-argument-in-python/

#Get outputs from .0 file and the .ctl file

def load_file(f):
    return np.fromfile(f, dtype='float32')

def create_netcdf(outputtype, time_idx, executor):
    timestep = "{:06d}".format(time_idx)
    

    #load .ctl file here and grab nz and variables
    control = open(f'cm1out_{outputtype}.ctl', 'r')
    #create x y and z dimension array for xarray

    varlist = []
    lon = []
    lat = []
    lev = []
    counter = 0
    for line in control:
        linelist = line.split()
        if not linelist:
            pass
        if linelist[0] == "endvars": #probably not necessary since we have the counter but whatever
            counter = 0

        if counter == 0:
            on_xlevs = False
            on_ylevs = False
            on_zlevs = False
            on_vars = False
        

        if on_xlevs:
            lon.append(linelist[0])
            counter -= 1
        if on_ylevs:
            lat.append(linelist[0])
            counter -= 1
        if on_zlevs:
            lev.append(linelist[0])
            counter -= 1
        if on_vars:
            varlist.append(linelist)
            counter -= 1

        if linelist[0] == 'xdef':
            num_cells = int(linelist[1])
            type = linelist[2]
            if type == "levels":
                counter = num_cells
                on_xlevs = True
            elif type == "linear":
                lon = np.linspace(float(linelist[3]), float(linelist[3]) + float(linelist[4]) * (num_cells - 1), num_cells)
        elif linelist[0] == 'ydef':
            num_cells = int(linelist[1])
            type = linelist[2]
            if type == "levels":
                counter = num_cells
                on_ylevs = True
            elif type == "linear":
                lat = np.linspace(float(linelist[3]), float(linelist[3]) + float(linelist[4]) * (num_cells - 1), num_cells)
        elif linelist[0] == 'zdef':
            num_z_levs = int(linelist[1])
            type = linelist[2]
            if type == "levels":
                counter = num_z_levs
                on_zlevs = True
            elif type == "linear":
                lev = np.linspace(float(linelist[3]), float(linelist[3]) + float(linelist[4]) * (num_z_levs - 1), num_z_levs)
        elif linelist[0] == "vars":
            num_vars = int(linelist[1])
            counter = num_vars
            on_vars = True
    

    ds = xr.Dataset(coords={'lev': lev, 'lat': lat, 'lon': lon})
    
    
    files = sorted(glob.glob(f"cm1out_*_{timestep}_{outputtype}.dat"))
    #file_data = np.zeros((n_cores))
    start = time.time()
    file_data = list(executor.map(load_file, files))
    end = time.time()
    print(f'Time for file loading = {end - start}s')

    cur_file_idx = np.zeros((n_cores), dtype = int)
    
    #make the loop of variables here
    start = time.time()
    for varnum, var_cur in enumerate(varlist):
        inc_z = (var_cur[1] != '0')

        if inc_z:
            global_data = np.zeros((num_z_levs, ny_total, nx_total), dtype='float32')
        else: #assume just these two options for now, I haven't seen anything else
            global_data = np.zeros((ny_total, nx_total), dtype='float32')


        for i, data in enumerate(file_data):
            rank = (int(files[i].split('_')[1]))
            # Calculate this rank's position in the global grid
            pos_x = rank % nodex
            pos_y = rank // nodex
            
            # Read binary data
            if inc_z:
                num_datum = int(num_z_levs * leny_each[pos_y] * lenx_each[pos_x])
                data_cur = data[cur_file_idx[i]: cur_file_idx[i] + num_datum].reshape(
                    (num_z_levs, leny_each[pos_y], lenx_each[pos_x]))
                global_data[:,
                        np.sum(leny_each[:pos_y]): np.sum(leny_each[:(pos_y + 1)]),
                        np.sum(lenx_each[:pos_x]): np.sum(lenx_each[:(pos_x + 1)])] = data_cur
            else:
                num_datum = int(leny_each[pos_y] * lenx_each[pos_x])
                data_cur = data[cur_file_idx[i]: cur_file_idx[i] + num_datum].reshape(
                    (leny_each[pos_y], lenx_each[pos_x]))
                global_data[
                        np.sum(leny_each[:pos_y]): np.sum(leny_each[:(pos_y + 1)]),
                        np.sum(lenx_each[:pos_x]): np.sum(lenx_each[:(pos_x + 1)])] = data_cur
            

            cur_file_idx[i] += num_datum


        var_desc = ' '.join(var_cur[3: -1])
        varname = var_cur[0]
        varunits = var_cur[-1]
        if inc_z:
            ds[varname] = (
                ('lev', 'lat', 'lon'),
                global_data,
                {'units': varunits, 'description': var_desc}
            )
        #print(f'Done var {varnum + 1} out of {num_vars}, num datum = {num_datum}, idx = {cur_file_idx[0]}')
    end = time.time()
    print(f'Time for data assembly was {end - start}s')
    # 3. Save to NetCDF
    start = time.time()
    ds.to_netcdf(f"cm1out_{timestep}_{outputtype}.nc")
    end = time.time()
    print(f'Time to write netcdf was {end - start}s')



start_time = int(sys.argv[1]) #take as an input
end_time = int(sys.argv[2]) #take as an input
filetypes = sys.argv[3:]


#start_time = 1
#end_time = 2
#filetypes = ['s', 'w'] #take as an input


#don't bother with u and v stagger, I doubt I have a need to output those vars

#https://stackoverflow.com/questions/40452536/how-to-open-a-file-only-using-its-extension
zerofile = open(glob.glob('*.0')[0], 'r')


for line in zerofile:
    linelist = line.split()
    if len(linelist) == 0:
        continue
    if linelist[0] == 'nx':
        nx_total = int(linelist[-1])
    elif linelist[0] == 'ny':
        ny_total = int(linelist[-1])
    elif linelist[0] == 'nodex':
        nodex = int(linelist[-1])
    elif linelist[0] == 'nodey':
        nodey = int(linelist[-1])
    elif linelist[0] == 'numprocs':
        n_cores = int(linelist[-1])
    elif linelist[0] == 'dx':
        break

    

global lenx_each
lenx_each = np.ones((nodex), dtype = int)*(nx_total // nodex)
extra_x = nx_total % nodex
lenx_each[:extra_x] = lenx_each[:extra_x] + 1


global leny_each
leny_each = np.ones((nodey), dtype = int)*(ny_total // nodey)
extra_y = ny_total % nodey
leny_each[:extra_y] = leny_each[:extra_y] + 1


with ProcessPoolExecutor() as executor:
    for outputtype in filetypes:
        for time_idx in range(start_time, end_time + 1):
            print(f'Starting outputtype {outputtype} timestep = {time_idx}')
            #output one netcdf per filetype per output time
            astart = time.time()
            create_netcdf(outputtype, time_idx, executor)
            aend = time.time()
            print(f'Time for total function was {aend - astart}s')
            print(' ')