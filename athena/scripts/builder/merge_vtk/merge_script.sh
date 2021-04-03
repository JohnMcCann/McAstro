#!/bin/sh

# Merges a single vtk dump from an mpi run
# USE: ./merge_vtk.sh DUMP CORELO COREHI LEV
# DUMP-which vtk dump, CORELO-lowest numerical value of procs which output dump
# COREHI-highest proc to output dump data, LEV-what lev this dump is
# For example suppose 10 procs carried out the calculation for a lev1 domain on
# procs [54-63]. To get dump #21 use: ./merge_vtk.sh 21 54 63 1

if test ! -d "id0"; then
  echo "Could not find id0... aborting merge..."
  exit 1
fi
base=`ls id0/ | grep 'vtk' | head -n 1 | cut -d '.' -f 1`
if test -z "$base"; then
  echo "No vtks found in id0... aborting merge..."
  exit 2
fi
dump=$1
start=$2
if [[ "$4" -gt 0 ]];then
  opath="-o vtk/lev$4/$base-lev$4.$(printf %04d $dump).vtk "
  if [[ "$2" -eq 0 ]];then
    opath+="id0/lev$4/$base-lev$4.$(printf %04d $dump).vtk "
    start+=1
  fi
  for (( j=$start; j<$3; j++ ));do
    opath+="id$j/lev$4/$base-id$j-lev$4.$(printf %04d $dump).vtk "
  done
else
  opath="-o vtk/$base.$(printf %04d $dump).vtk "
  s="$2"
  if [[ "$2" -eq 0 ]]; then
    opath+="id0/$base.$(printf %04d $dump).vtk "
    s+=1
  fi
  for (( j="$s"; j<"$3"; j++ ));do
    opath+="id$j/$base-id$j.$(printf %04d $dump).vtk "
  done
fi
echo "$opath"
./join_vtk "$opath"
