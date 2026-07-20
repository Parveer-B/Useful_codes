#!/bin/bash

#SBATCH --job-name=netcdfconversion
#SBATCH --output %xconvert.out.%j 
#SBATCH --error %xconvert.err.out.%j 
#SBATCH --time=02:00:00
#SBATCH --partition=compute 
#SBATCH --ntasks-per-node=192
#SBATCH --nodes=1
#SBATCH --mail-type=ALL 
#SBATCH --mail-user=parveer.banwait@mail.utoronto.ca

module load StdEnv/2023 gcc/12.3 openmpi/4.1.5
module load cdo

cdo -f nc4 import_binary cm1out_metadata.ctl cm1out_metadata.nc
cdo -f nc4 import_binary cm1out_stats.ctl cm1out_stats.nc

sed -i "8s/.*/tdef         1 linear 00:00Z01JAN0001 1YR/" cm1out_s.ctl
sed -i "8s/.*/tdef         1 linear 00:00Z01JAN0001 1YR/" cm1out_w.ctl
#Note! If using z-stretching the 8 must be modified to whatever line this is on!

for i in {000001..000026}; do
	(
		cp cm1out_s.ctl tmp_s_${i}.ctl
		cp cm1out_w.ctl tmp_w_${i}.ctl
		sed -i "1s/.*/dset ^cm1out_${i}_s.dat/" tmp_s_${i}.ctl
		cdo -f nc4 import_binary tmp_s_${i}.ctl cm1out_${i}_s.nc
		sed -i "1s/.*/dset ^cm1out_${i}_w.dat/" tmp_w_${i}.ctl
		cdo -f nc4 import_binary tmp_w_${i}.ctl cm1out_${i}_w.nc
		
		rm "tmp_s_${i}.ctl" "tmp_w_${i}.ctl"
	) &
done