#!/bin/bash

# Fixed scheduler directives that do not vary run to run
# replace this line with directive_lines

################################################################################
############################## USER SET VARIABLES ##############################
################################################################################

# Scheduler directives that vary run to run

# Cluster variables
athena_path=""                           # athena_ae directory
scratch=""                               # user sratch directory
modules=()                               # modules to be loaded

# Run variables
# repalce this line with ncores_line
run_name=""                              # name of run
run_tag=""                               # subname/tag of run
test_path="${athena_path}/tst/"          # athinput directory
test_file="${test_path}/athinput."       # athinput file
restart_run=false                        # if run is a restart (boolean)
restart_file=""                          # id0 restart file
################################################################################
############################ END USER SET VARIABLES ############################
################################################################################

# Log intro
echo "began: $(date)"
echo "pwd: $(pwd)"
echo "host: $(hostname) on ${SLURM_CLUSTER_NAME}"
echo "nodes: ${SLURM_JOB_NODELIST} (--nodes=${SLURM_JOB_NUM_NODES})"
echo "ntasks: ${SLURM_NTASKS}"
echo "ntasks-per-node: ${SLURM_NTASKS_PER_NODE}"
echo "mem-per-cpu: ${SLURM_MEM_PER_CPU}"

# Load modules
if test "${#modules[@]}" -gt 0;then
  module purge
  for mod in ${modules[@]};do
    module load "$mod"
  done
  echo ""; module list; echo ""
fi

# Athena_AE paths and directory creations
## executable directory
bin_path="${athena_path}/bin"
## athena_ae sims storage
if test "$athena_path" != "$scratch" -a -n "$scratch"; then
  sim_path="${scratch}/athena_ae_sims"
  if test ! -d "$sim_path"; then
    mkdir -p "$sim_path"
  fi
  if test ! -L "sim"; then
    ln -s "$sim_path" "sim"
  fi
else # athena_path is scratch
  sim_path="${athena_path}/sim"
  if test ! -d "$sim_path"; then
    mkdir -l "$sim_path"
  fi
fi
## current run directory
run_path="${sim_path}/${run_name}"
## raw outputs
raw_path="${run_path}/raw"
if test ! -d "$raw_path"; then
  mkdir -p "$raw_path"
fi
## general post directory
post_path="${run_path}/post"
## info
info_path="${post_path}/info"
if test ! -d "$info_path"; then
  mkdir -p "$info_path"
fi
## analysis
anly_path="${post_path}/anly"
if test ! -d "$anl_path"; then
  mkdir -p "$anly_path"
fi

# Savestate executable, atinput, problem.c, config.log, and git
cp "$bin_path"/athena "$info_path"
cp "$test_file" "$info_path"/athinput
cp "$athena_path"/src/problem.c "$info_path"
cp "$athena_path"/config.log "$info_path"
if test -f git.log; then
  cp "$athena_path"/git.log "$info_path"
fi

# replace this line with script_lines

# build mpirun command
sim_cmd="mpirun -n ${ncores} ${bin_path}/athena -d ${raw_path} -i ${test_file}"
if "$restart_run"; then
  echo "restart: ${restart_file}"; echo ""
  sim_cmd="${sim_cmd} -r ${restart_file}"
fi
logging="> ${info_path}/${run_name}.txt 2> ${info_path}/${run_name}.err"
sim_cmd="${sim_cmd} ${logging}"

# echo mpirun command
echo "simulation execution:"
cmd_str="$sim_cmd"
dlmtr="${bin_path}/athena"
echo "${cmd_str%%$dlmtr*}"
cmd_str=${cmd_str#*"$dlmtr"};
cmd_str="${dlmtr}${cmd_str}"
dlmtr=" -"
array=();
temp="${cmd_str}${dlmtr}"
while [[ $temp ]]; do
  array+=( "${temp%%$dlmtr*}" );
  temp=${temp#*"$dlmtr"};
done;
logger=${array[${#array[@]}-1]}
unset array[${#array[@]}-1]
echo "  ${array[0]}"
for i in "${array[@]:1}"; do
  echo "    -$i"
done
dlmtr=">"
echo "    -${logger%%$dlmtr*}"
logger=${logger#*"$dlmtr"};
echo "  >${logger%%"2>"*}"
echo " 2>${logger#*"2>"}"

# Execute simulation
eval $sim_cmd

# Log extro
echo "Finished: $(date)"