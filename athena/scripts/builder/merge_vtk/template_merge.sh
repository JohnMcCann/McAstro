#!/bin/sh
## Description: Generate and submit job scripts to merge .vtk outputs from
##              MPI runs
## Inputs: $1=first dump to be merged (optional)
##         $2=last dump to be merged (optional)

# Determine range of dumps to be merged,
if [[ -n "$1" && -n "$2" ]]; then
  s_in=$(($1+1))
  s_en=$(($2+1))
else
  s_in="`ls vtk/ | grep 'vtk' | tail -n 1 | cut -d '.' -f 2 | sed 's/^0*//'`"
  if [[ -n "$s_in" ]]; then
    s_in=$(($s_in+2))
  else
    s_in="1"
  fi
  s_en="`ls id0/ | grep 'vtk' | tail -n 1 | cut -d '.' -f 2 | sed 's/^0*//'`"
  s_en=$(($s_en+1))
fi
if [[ $s_in -gt $s_en ]]; then
  echo "Automatic detection found no dumps that need to be merged."
  echo "Supply a lower and upper bound as inputs for the range of dumps to manually merge."
  exit
fi

# Get the range of cores that corrispond to each level
base=`ls id0/ | grep 'vtk' | head -n 1 | cut -d '.' -f 1`
nlev=`ls -l id0 | grep -c "lev.*"`
nfol=`ls -l . | grep -c 'id'`
core=()
ecore=()
size=()
for lev in `seq 0 1 $nlev`;do
  ls=""
  bl=""
  first=0
  if [[ $lev -ne 0 ]];then
    ls="/lev$lev"
    bl="-lev$lev"
    mkdir -p vtk/lev$lev
  fi
  for fol in `seq 0 $nfol`;do
    bi=""
    if [[ $fol -ne 0 ]];then
      bi="-id$fol"
    fi
    if test "$first" -ne 1 && test "$(ls id$fol$ls/*$(printf %04d $(($s_in-1))).vtk 2>/dev/null | wc -l)" -ne 0;then 
      core+=($fol)
      size+=(`echo "id$fol$ls/$base$bi$bl.$(printf %04d $(($s_in-1))).vtk" | xargs du -k | cut -f1`)
      first=1
    fi
    if test $first -eq 1 && test "$(ls id$fol$ls/*$(printf %04d $(($s_in-1))).vtk 2>/dev/null | wc -l)" -eq 0;then
      ecore+=($fol)
      break
    fi
  done
done

# Sort the levels so that the most expensive ones are done first
order=()
num_core=()
core+=($nfol) # Add last folder for periodic boundary
for (( i=0; i<${#size[@]}; i++ ));do
  order+=($i)
  num_core+=($((${core[$(($i+1))]}-${core[$i]})))
  size[$i]=$((size[$i]*(${core[$(($i+1))]}-${core[$i]})))
done
for (( i=0; i<${#size[@]}-1; i++ ));do
  large=${size[$i]}
  old_order=${order[$i]}
  location=$i
  for (( j=$i+1; j<${#size[@]}; j++ ));do
    if [[ $large -lt ${size[$j]} ]];then
      large=${size[$j]}
      order[$i]=${order[$j]}
      location=$j
    fi
  done
  order[$location]=$old_order
  size[$location]=${size[$i]}
  size[$i]=$large
done
unset core[${#core[@]}-1] # drop added folder

# Some cluster limits job arrays to X jobs per submission
joblimit=500
while test $((s_en-s_in)) -gt "$joblimit";do
  ilist+=("$s_in")
  s_in=$((s_in+500))
  elist+=("$s_in")
  s_in=$((s_in+1))
done
ilist+=("$s_in")
elist+=("$s_en")

# Modify and submit the scripts for each level in the correct order
# even if ${num_core[$lev]} -lt 2, use join_vtk to sanitize vtks