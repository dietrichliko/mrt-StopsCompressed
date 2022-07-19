#!/bin/bash

for f in samples/*.csv
do
   name="$(basename -s .csv "$f")"
   ./check_files.py "$f" |& tee "samples/$name.log"
done
