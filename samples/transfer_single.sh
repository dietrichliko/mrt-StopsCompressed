#!/bin/sh

while read -r dataset
do
    echo rucio add-rule --ask-approval cms:$dataset 1 T2_AT_Vienna
done <<EOF
/SingleElectron/Run2016B-ver1_HIPM_UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD
/SingleElectron/Run2016B-ver2_HIPM_UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD
/SingleElectron/Run2016C-HIPM_UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD
/SingleElectron/Run2016D-HIPM_UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD
/SingleElectron/Run2016E-HIPM_UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD
/SingleElectron/Run2016F-HIPM_UL2016_MiniAODv2_NanoAODv9-v2/NANOAOD
/SingleElectron/Run2016F-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD
/SingleElectron/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD
/SingleElectron/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD
/SingleElectron/Run2017B-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
/SingleElectron/Run2017C-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
/SingleElectron/Run2017D-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
/SingleElectron/Run2017E-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
/SingleElectron/Run2017F-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
/EGamma/Run2018A-UL2018_MiniAODv2_NanoAODv9-v1/NANOAOD
/EGamma/Run2018B-UL2018_MiniAODv2_NanoAODv9-v1/NANOAOD
/EGamma/Run2018C-UL2018_MiniAODv2_NanoAODv9-v1/NANOAOD
/EGamma/Run2018D-UL2018_MiniAODv2_NanoAODv9-v3/NANOAOD
EOF
