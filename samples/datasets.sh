#!/bin/sh

dasgoclient --query="dataset dataset=/SingleMuon/Run*MiniAODv2_NanoAODv9-*/NANOAOD"
dasgoclient --query="dataset dataset=/SingleElectron/Run*MiniAODv2_NanoAODv9-*/NANOAOD"
dasgoclient --query="dataset dataset=/EGamma/Run*MiniAODv2_NanoAODv9-*/NANOAOD"
