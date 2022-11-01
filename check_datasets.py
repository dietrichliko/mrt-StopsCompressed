#!/usr/bin/env python


import pathlib
import ROOT

NTUPLE_DIR = pathlib.Path("/scratch-cbe/users/dietrich.liko/StopsCompressed/nanoTuples")


def main(skim: str) -> None:

    for dir in NTUPLE_DIR.glob(f"*/{skim}/*Run*"):
        if not dir.is_dir():
            continue
        print(f"Scanning {dir.name} ...")
        branches: list[set[str]] = []
        for i, root_file in enumerate(dir.iterdir()):
            inp_file = ROOT.TFile(str(root_file), "READ")
            inp_chain = inp_file.Get("Events")

            branches.append(set(x.GetName() for x in inp_chain.GetListOfBranches()))
            inp_file.Close()

        all = set()
        for b in branches:
            all |= b

        for i, b in enumerate(branches):
            names = [n for n in all - b if not n.startswith("HLT_")]
            if names:
                print(i, names)


if __name__ == "__main__":
    main("DoubleLep")
