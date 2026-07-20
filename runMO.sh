#!/bin/bash

#SBATCH --job-name=03_22_exp59_mid_150m_nozst_intsd_ens1
#SBATCH --output %x.out.%j 
#SBATCH --error %x.err.out.%j 
#SBATCH --time=1-00:00:00
#SBATCH --partition=compute 
#SBATCH --ntasks-per-node=192
#SBATCH --nodes=2
#SBATCH --mail-type=ALL 
#SBATCH --mail-user=parveer.banwait@mail.utoronto.ca

## Comments:
echo `cpu_codename -c`

module purge
ml gcc/13.3 openmpi/5.0.3 hdf5/1.14.5

export PATH=/home/cdimaria/libraries_gcc/netcdf/bin:$PATH 
export LD_LIBRARY_PATH=/home/cdimaria/libraries_gcc/netcdf/lib:$LD_LIBRARY_PATH
export CPATH=/home/cdimaria/libraries_gcc/netcdf/include:$CPATH

export EXP=/scratch/parveerb/CM1_stuff/data/realistic_supercells
export EXPFAM=supercells_150m_periodic_ensembleruns
export NAME=03_22_exp59_mid_150m_nozst_intsd_ens1 ## MODIFY EVERY TIME
export RUNSH=runMO.sh

mkdir $EXP/$EXPFAM/$NAME
mkdir $EXP/$EXPFAM/$NAME/run
#mkdir $EXP/$EXPFAM/$NAME/src

cp cm1.exe		$EXP/$EXPFAM/$NAME/run/.
cp onefile.F		$EXP/$EXPFAM/$NAME/run/.
cp RRTMG_LW_DATA	$EXP/$EXPFAM/$NAME/run/.
cp RRTMG_SW_DATA	$EXP/$EXPFAM/$NAME/run/.
cp input_sounding	$EXP/$EXPFAM/$NAME/run/.
cp get_nc.sh	$EXP/$EXPFAM/$NAME/run/.
cp $RUNSH		$EXP/$EXPFAM/$NAME/run/.
cp namelist.input 	$EXP/$EXPFAM/$NAME/run/.
cp -r ../src		$EXP/$EXPFAM/$NAME/.
cp LANDUSE.TBL		$EXP/$EXPFAM/$NAME/run/.
cp run_rst.sh	$EXP/$EXPFAM/$NAME/run/.

cd $EXP/$EXPFAM/$NAME/run

mpirun ./cm1.exe >> 03_22_exp59_mid_150m_nozst_intsd_ens1.0

#sed -i "30s/.*/ irst      =  1," namelist.input
#sbatch run_rst.sh
