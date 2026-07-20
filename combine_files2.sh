#!/bin/bash

#SBATCH --job-name=combine_multi_exp68_23_h5netcdf
#SBATCH --output %x.out.%j 
#SBATCH --error %x.err.out.%j 
#SBATCH --time=02:15:00
#SBATCH --partition=compute 
#SBATCH --ntasks-per-node=192
#SBATCH --nodes=1
#SBATCH --mail-type=ALL 
#SBATCH --mail-user=parveer.banwait@mail.utoronto.ca

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 hdf5 netcdf netcdf-fortran python/3.11.5 mpi4py

source ~/TriPyEnv/bin/activate #switch to your venv

for i in {23..23}
do
    echo "Processing timestep $i..."
    python3 combine_multinew_parallelized_new.py $i $i s
    python3 combine_multinew_parallelized_new.py $i $i w
done

deactivate