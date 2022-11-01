#!/usr/bin/env python

import pathlib
import sys

import ROOT

PATH = pathlib.Path(
    "/scratch-cbe/users/dietrich.liko/StopsCompressed/nanoTuples/compstops_UL16v9_nano_v9/DoubleLep/DYJetsToLL_M50_LO"
)


def check(path: pathlib.Path) -> None:

    # ROOT.EnableImplicitMT()
    chain = ROOT.TChain("Events")
    for p in path.iterdir():
        chain.Add(str(p))

    print(f"Chain {chain.GetEntries()}")

    df = ROOT.RDataFrame(chain)

    # events = df.Count()
    # sum_weights = df.Sum("weight")

    weights = [
        "weight",
        "reweightPU",
        "reweightBTag_SF",
        "reweightL1Prefire",
        "reweightLeptonSF",
        "{}",
    ]

    df.Display(["weight", "reweightPU", "reweightLeptonSF"], 10).Print()
    sys.exit()

    df = df.Define("the_weight", "*".join(weights).format(27.5))
    sum_new_weights = df.Sum("the_weight")
    print(f"Events {events.GetValue()}")
    print(f"Sum weights {sum_weights.GetValue()}")
    print(f"Sum new weights {sum_new_weights.GetValue()}")


if __name__ == "__main__":
    check(PATH)
