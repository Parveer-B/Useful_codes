#!/bin/bash

#SBATCH --job-name=0716_exp59_mid__rst60-90
#SBATCH --output %x.out.%j 
#SBATCH --error %x.err.out.%j 
#SBATCH --time=1-00:00:00
#SBATCH --partition=compute 
#SBATCH --ntasks-per-node=192
#SBATCH --nodes=2
#SBATCH --mail-type=ALL 
#SBATCH --mail-user=parveer.banwait@mail.utoronto.ca

#EDIT LINES 74 and 94!!!


# Configuration variables
LOG_FILE="moreoutputtestt.0"
VERT_LEVELS=300
EXPNUM=59 #EDIT

# Export environment paths upfront
export PATH=/home/cdimaria/libraries_gcc/netcdf/bin:$PATH 
export LD_LIBRARY_PATH=/home/cdimaria/libraries_gcc/netcdf/lib:$LD_LIBRARY_PATH
export CPATH=/home/cdimaria/libraries_gcc/netcdf/include:$CPATH

# Define a function to process outputs for a specific range of indices
process_cm1_output() {
    local start_idx=$1
    local end_idx=$2

    # Step 1: Convert raw binary data to NetCDF using CDO
    module purge
    module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 cdo

    sed -i "8s/.*/tdef         1 linear 00:00Z01JAN0001 1YR/" cm1out_s.ctl
    sed -i "8s/.*/tdef         1 linear 00:00Z01JAN0001 1YR/" cm1out_w.ctl

    # Run background processes for file conversion
    for i in $(seq -f "%06g" "$start_idx" "$end_idx"); do
        (
            cp cm1out_s.ctl "tmp_s_${i}.ctl"
            cp cm1out_w.ctl "tmp_w_${i}.ctl"
            
            sed -i "1s/.*/dset ^cm1out_${i}_s.dat/" "tmp_s_${i}.ctl"
            cdo -f nc4 import_binary "tmp_s_${i}.ctl" "cm1out_${i}_s.nc"
            
            sed -i "1s/.*/dset ^cm1out_${i}_w.dat/" "tmp_w_${i}.ctl"
            cdo -f nc4 import_binary "tmp_w_${i}.ctl" "cm1out_${i}_w.nc"
            
            rm "tmp_s_${i}.ctl" "tmp_w_${i}.ctl"
            rm "cm1out_${i}_s.dat" "cm1out_${i}_w.dat"
        ) &
    done
    wait # Keeps python from running until all background conversions finish

    # Step 2: Run Python compression script
    module purge
    module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 hdf5 netcdf netcdf-fortran python/3.11.5
    source ~/my_env4/bin/activate

    python compress_symlog.py $VERT_LEVELS $EXPNUM $(seq "$start_idx" "$end_idx")

    # Step 3: Clean up temporary uncompressed NetCDF files
    for i in $(seq -f "%06g" "$start_idx" "$end_idx"); do
        rm "cm1out_${i}_s.nc" "cm1out_${i}_w.nc"
    done
}

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================

# Format: "rst_num:start_index:end_index"
RUNS=(
    "3:8:17"
    "4:18:27"
    "5:28:37"
)

for run_info in "${RUNS[@]}"; do
    IFS=":" read -r rst_num start_idx end_idx <<< "$run_info"
    
    echo "=== Starting Run $rst_num (Indices $start_idx to $end_idx) ==="

    # 1. Run CM1 Simulation
    module purge
    ml gcc/13.3 openmpi/5.0.3 hdf5/1.14.5
    
    sed -i "31s/.*/ rstnum      =  ${rst_num},/" namelist.input
    
    mpirun ./cm1.exe >> "$LOG_FILE"

    # 2. Handle Restart Files (Skips deleting run 1 to preserve progress)
    if [ "$rst_num" -ne 3 ]; then 
        rst_padded=$(printf "%06d" "$rst_num")
        rm cm1rst_${rst_padded}_*.dat
    fi

    # 3. Post-Process Data
    process_cm1_output "$start_idx" "$end_idx"
done

# ==========================================
# FINAL POST-RUN CLEANUP
# ==========================================
echo "=== Finalizing Metadata ==="
module purge
module load StdEnv/2023 gcc/12.3 openmpi/4.1.5 cdo
cdo -f nc4 import_binary cm1out_metadata.ctl cm1out_metadata.nc
cdo -f nc4 import_binary cm1out_stats.ctl cm1out_stats.nc
