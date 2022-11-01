#!/usr/bin/env python
import csv
import logging
import os
import pathlib
from typing import Any
from typing import TextIO

import click
import ruamel.yaml

logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(name)s - %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)
log = logging.getLogger()

SKIMS = ["Met", "MetLepEnergy", "DoubleLep"]
PERIODES = ["Run2016preVFP", "Run2016postVFP", "Run2017", "Run2018"]

PATH = "/store/user/liko/StopsCompressed/nanoTuples"


def make_entry(v: dict[str, Any]) -> dict[str, Any]:

    entry: dict[str, Any] = {"name": v["Name"], "type": v["Type"]}
    title = v["Title"].strip()
    if title:
        entry["title"] = title
    if v["Path"].startswith("#"):
        entry["hidden"] = True
    if v["Color"]:
        if "attributes" not in entry:
            entry["attributes"] = {}
        entry["attributes"]["color"] = v["Color"]
    if v["integrated_luminosity"]:
        if "attributes" not in entry:
            entry["attributes"] = {}
        entry["attributes"]["integrated_luminosity"] = float(v["integrated_luminosity"])
    if v["trigger"]:
        if "attributes" not in entry:
            entry["attributes"] = {}
        entry["attributes"]["trigger"] = v["trigger"].split()

    return entry


@click.command
@click.argument("output", type=click.File(mode="w"))
@click.option(
    "--skim",
    default="Met",
    type=click.Choice(SKIMS),
    help="Generate sample definition for a specific skim",
)
def main(output: TextIO, skim: str) -> None:
    """Generate sample definition for a skim."""
    log.info("Writing %s", output.name)

    with ruamel.yaml.YAML(output=output) as yaml:
        yaml.explicit_start = True

        for p in PERIODES:

            rpath = pathlib.PurePath("")
            samples: dict[pathlib.PurePath, Any] = {rpath: []}
            data = {
                "name": os.path.splitext(os.path.basename(output.name))[0],
                "period": p,
                "samples": samples[rpath],
            }
            fname = f"{skim} - {p}.csv"
            log.info("Reading %s", fname)
            with open(fname, "r") as inp:
                reader = csv.DictReader(inp)

                for v in reader:
                    if v["Tag"]:
                        path = pathlib.PurePath(v["Path"].lstrip("#"))
                        cpath = rpath
                        for p in path.parts:
                            pp = cpath / p
                            if pp not in samples.keys():
                                samples[pp] = []
                                samples[cpath].append(
                                    {
                                        "name": p,
                                        "type": v["Type"],
                                        "samples": samples[pp],
                                    }
                                )
                            cpath = pp
                        entry = make_entry(v)
                        entry["directory"] = f'{PATH}/{v["Tag"]}/{skim}/{v["Name"]}'
                        samples[path].append(entry)
                    else:
                        path = pathlib.PurePath(v["Name"])
                        samples[path] = []
                        entry = make_entry(v)
                        entry["samples"] = samples[path]
                        samples[rpath].append(entry)

                yaml.dump(data)


if __name__ == "__main__":
    main()
