#!/usr/bin/env python
"""Modern ROOT Tools example01."""
import json
import logging
import os
import pathlib
import sys
from mrtools import cache
from mrtools import config
from mrtools import model
from mrtools import plotter
from mrtools import utils
from mrtools.model import SampleType as ST
from typing import Any
from typing import Iterator
from typing import Tuple
from typing import Union

import click
import ROOT
import ruamel.yaml as yaml


ROOT.PyConfig.IgnoreCommandLineOptions = True

logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(name)s - %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)
log = logging.getLogger("mrtools")
cfg = config.get()

BASE_DIR = pathlib.Path(__file__).absolute().parent

PERIODS = [
    "Run2016preVFP",
    "Run2016postVFP",
    "Run2017",
    "Run2018",
]

DEFAULT_OUTPUT = pathlib.Path("/scratch-cbe/users", os.environ["USER"], "WPT")
DEFAULT_NAME = "wpt01_{period}"

DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/MetLepEnergy_nanoNtuple_v6.yaml"
DEFAULT_HISTOS_FILE = BASE_DIR / "wpt01.histos.yaml"


def get_samples(
    sc: Any,
    period: str,
    sample_names: Union[None, str, list[str]],
    types: model.SampleType,
) -> list[model.Sample]:
    """Get samples per name."""
    if sample_names:
        samples = sc.find(period, sample_names)
    else:
        samples = sc.list(period, types=types)

    return list(samples)


def get_h(
    tree: Any, hd: dict[str, Any], samples: list[model.Sample]
) -> list[Tuple[Any, str, int]]:
    """Get histograms from file."""
    histos: list[Tuple[Any, str, int]] = []
    name = hd["name"]
    for s in samples:
        subdir = "_".join(s.path.parts[3:])
        h = tree.Get(f"{subdir}/{name}")
        if not h:
            log.error("Histogram %s/%s not found.", subdir, name)
            continue
        h.SetName(s.name)
        if "color" in s.attrs:
            color = s.attrs["color"]
            if isinstance(color, str) and color[0] == "k":
                color = eval(f"ROOT.{color}")
            color = int(color)
        else:
            color = None

        histos.append((h, s.title, color))

    return histos


@click.command
@click.option(
    "--config-file",
    default=None,
    type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path),
    help="Configuration file",
)
@click.option("--site", default="", help="Site name")
@click.option(
    "--name",
    default=DEFAULT_NAME,
    help="Name for files",
    show_default=True,
)
@click.option(
    "--period",
    default=PERIODS,
    type=click.Choice(PERIODS, case_sensitive=False),
    help="Datataking period (default: all)",
    multiple=True,
)
@click.option(
    "--samples-file",
    type=click.Path(exists=True, resolve_path=True),
    default=[DEFAULT_SAMPLE_FILE],
    multiple=True,
    help="Sample definitions",
    show_default=True,
)
@click.option(
    "--histos-file",
    type=click.Path(exists=True, resolve_path=True),
    default=DEFAULT_HISTOS_FILE,
    help="Histogram definitions",
    show_default=True,
)
@click.option(
    "--output",
    default=DEFAULT_OUTPUT,
    type=click.Path(file_okay=False, writable=True, path_type=pathlib.Path),
    help="Output directory",
    show_default=True,
)
@utils.click_option_logging(log)
def main(
    config_file: pathlib.Path,
    site: str,
    name: str,
    period: list[str],
    samples_file: Iterator[pathlib.Path],
    histos_file: pathlib.Path,
    output: pathlib.Path,
):
    """Run example01."""
    cfg.load(config_file, site)

    ROOT.gROOT.SetBatch()
    plotter.tdr_style()

    sc = cache.SamplesCache()
    for s in samples_file:
        sc.load(s)

    yaml_parser = yaml.YAML(typ="safe")
    with open(histos_file, "r") as inp:
        histos = yaml_parser.load(inp)

    stat: dict[str, Any] = {}
    for p in period:
        output_path = output / name.format(period=p)
        inp_root_path = output_path.with_suffix(".root")
        if not inp_root_path.exists():
            log.fatal("Input %s does not exists", inp_root_path)
            sys.exit()
        log.info("Reading histograms from %s", inp_root_path)
        inp_root = ROOT.TFile(str(inp_root_path), "READ")

        out_root_path = output_path.with_suffix(".plots.root")
        log.info("Writing plots to %s", out_root_path)
        out_root = ROOT.TFile(str(out_root_path), "RECREATE")

        with open(output_path.with_suffix(".json"), "r") as input_json:
            stat = json.load(input_json)

        output_path.mkdir(parents=True, exist_ok=True)

        for h in histos:

            df = h["dataframe"]
            log.debug("Histograms in dataframe %s", df)

            dat_samples = get_samples(sc, p, h.get("data_samples"), ST.DATA)
            bkg_samples = get_samples(
                sc, p, h.get("background_samples"), ST.BACKGROUND
            )
            sig_samples = get_samples(sc, p, h.get("signal_samples"), ST.SIGNAL)

            dat_names = [s.name for s in dat_samples]
            bkg_names = [s.name for s in bkg_samples]
            sig_names = [s.name for s in sig_samples]
          
            log.debug("Data: %s", ", ".join(dat_names))
            log.debug("Background: %s", ", ".join(bkg_names))
            log.debug("Signal: %s", ", ".join(sig_names))

            nr_events = stat[dat_names[0]][f"{df}_nr_events"]
            sum_weights = sum(
                stat[s][f"{df}_sum_weights"] for s in bkg_names
            )
            scale = nr_events / sum_weights
            log.info(
                "Dataframe %s - Data events %d - Background %.1f - Scale %.3f",
                df,
                nr_events,
                sum_weights,
                scale,
            )
            for h_def in h.get("Histo1D", []):
                hist = h_def["name"]
                title = h_def.get("title", hist)
                histos_dat = get_h(inp_root, h_def, dat_samples)
                histos_bkg = get_h(inp_root, h_def, bkg_samples)
                histos_sig = get_h(inp_root, h_def, sig_samples)
                if not histos_dat:
                    log.error("No data found for %s", hist)
                    continue
                if not histos_bkg:
                    log.error("No background found for %s", hist)
                    continue
                plotter.stackplot(
                    output_path / f"{hist}_lin.png",
                    histos_dat,
                    histos_bkg,
                    histos_sig,
                    x_label=title,
                    # ratio_plot=False,
                    scale=scale,
                )

                histos_dat = get_h(inp_root, h_def, dat_samples)
                histos_bkg = get_h(inp_root, h_def, bkg_samples)
                histos_sig = get_h(inp_root, h_def, sig_samples)
                plotter.stackplot(
                    output_path / f"{hist}_log.png",
                    histos_dat,
                    histos_bkg,
                    histos_sig,
                    logy=True,
                    x_label=title,
                    # ratio_plot=False,
                    scale=scale,
                )

        inp_root.Close()
        out_root.Close()


if __name__ == "__main__":
    main()
