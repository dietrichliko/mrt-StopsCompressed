#!/usr/bin/env python

import json
import subprocess

import ROOT

DASGOCLIENT = "/cvmfs/cms.cern.ch/common/dasgoclient"


def main(dataset: str) -> None:

    ROOT.EnableImplicitMT()

    cmd = [DASGOCLIENT, "-json", f"-query=file dataset={dataset}"]
    output = subprocess.run(
        cmd, stdout=subprocess.PIPE, encoding="UTF-8", check=True
    ).stdout
    urls: list[str] = []
    for item in json.loads(output):
        urls += [
            f'root://eos.grid.vbc.ac.at//eos/vbc/experiments/cms{f["name"]}'
            for f in item["file"]
        ]

    print(f"Dataset {dataset} - Files {len(urls)}")

    chain = ROOT.TChain("Events")
    for url in urls:
        chain.Add(url)

    print(f"Nr of entries: {chain.GetEntries()}")


if __name__ == "__main__":
    main(
        "/DYJetsToLL_M-50_TuneCP5_13TeV-madgraphMLM-pythia8/RunIISummer20UL16RECOAPV-106X_mcRun2_asymptotic_preVFP_v8-v1/AODSIM"
    )
