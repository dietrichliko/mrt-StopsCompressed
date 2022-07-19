#!/usr/bin/env python
import csv
import logging
import os
import pathlib
import sys

import click
import ROOT

ROOT.PyConfig.IgnoreCommandLineOptions = True
logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PATH = pathlib.Path("/scratch-cbe/users/dietrich.liko/StopsCompressed/nanoTuples/")


def check_file(path: pathlib.Path):

    df = ROOT.RDataFrame("Events", str(path))
    events = df.Count()
    sum_weights = df.Sum("weight")
    events.GetValue()
    sum_weights.GetValue()


@click.command
@click.argument("input", type=click.Path(exists=True, path_type=pathlib.Path))
@click.option("--verify/--no-verify", default=False, help="Try readin the files.")
@click.option("--root-threads", default=4, help="Number of root threads.")
def main(input: pathlib.Path, verify: bool, root_threads: int) -> None:

    log.setLevel(logging.DEBUG)
    ROOT.gROOT.SetBatch()
    ROOT.EnableImplicitMT(root_threads)
    skim, period = input.stem.split(" - ")
    log.info("Skim %s, Period %s", skim, period)
    tot1 = 0
    tot2 = 0
    with open(input, "r") as csv_input:
        for e in csv.DictReader(csv_input):
            prefix = e["Path"]
            name = e["Name"]
            tag = e["Tag"]
            if prefix.startswith("#") or not tag:
                continue
            nr = int(e["#Files"])
            icnt = 0
            sample_dir = PATH / f"{tag}/{skim}/{name}"
            if sample_dir.exists():
                files = set(p for p in sample_dir.iterdir())
                if nr == 1:
                    path = sample_dir / f"{name}.root"
                    try:
                        files.remove(path)
                        if verify:
                            check_file(path)
                        icnt += 1
                    except KeyError:
                        log.debug("Missing %s", path)
                else:
                    for i in range(nr):
                        path = sample_dir / f"{name}_{i}.root"
                        try:
                            files.remove(path)
                            if verify:
                                check_file(path)
                            icnt += 1
                        except KeyError:
                            log.debug("Missing %s", path)
                for f in files:
                    log.warning("Extra file %s", f)
            else:
                icnt = 0
                if nr == 1:
                    log.debug("Missing %s", sample_dir / f"{name}.root")
                else:
                    for i in range(nr):
                        log.debug("Missing %s", sample_dir / f"{name}_{i}.root")
	    
            tot1 += icnt
            tot2 += nr
            if not prefix:
                log.info("%-50s: %3d/%3d", name, icnt, nr)
            else:
                log.info("%-50s: %3d/%3d", f"{prefix}/{name}", icnt, nr)
    log.info("Total: %3d/%3d", tot1, tot2)


if __name__ == "__main__":
    main()
