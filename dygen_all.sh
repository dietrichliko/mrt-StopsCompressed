#!/bin/sh


for period in 'Run2016preVFP' 'Run2016postVFP' 'Run2017' 'Run2018'
#for period in 'Run2016preVFP' 'Run2016postVFP' 
do
    echo "$period No HT Bins"
    ./dygen.py -p $period --no-ht-bins -l DEBUG -o plots/dygen_${period}_no_ht_bins.root
    echo "$period HT Bins" 
    ./dygen.py -p $period --ht-bins -l DEBUG -o plots/dygen_${period}_ht_bins.root
done
