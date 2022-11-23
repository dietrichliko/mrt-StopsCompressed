#!/usr/bin/env python
import logging
import os
import pathlib
from mrtools import cache
from mrtools import config
from mrtools import model
from mrtools import plotter
from mrtools import utils
from typing import Any
from typing import Tuple

import click
import ROOT

ROOT.PyConfig.IgnoreCommandLineOptions = True

logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(name)s - %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.WARNING,
)
log = logging.getLogger("mrtools")
cfg = config.get()

BASE_DIR = pathlib.Path(__file__).absolute().parent
DEFAULT_OUTPUT = pathlib.Path(
    "/scratch-cbe/users", os.environ["USER"], "StopsCompressed/plots"
)

PERIODS = [
    "Run2016preVFP",
    "Run2016postVFP",
    "Run2017",
    "Run2018",
]

DEFAULT_NAME = "wpt"

DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/MetLepEnergy_nanoNtuple_v7.yaml"


ISR_CORRECTIONS = [
    1.0,
    1.052,
    1.179,
    1.150,
    1.057,
    1.000,
    0.912,
    0.783,
]


def get_histo(tree: Any, name: str, sample: model.SampleBase) -> Tuple[Any, str, int]:
    """Get histogram from sample subdir."""
    subdir = "_".join(sample.path.parts[3:])
    h = tree.Get(f"{subdir}/{name}")
    if not h:
        log.error("Histogram %s/%s not found.", subdir, name)
        return None, "", 0

    h.SetName(sample.name)
    if "color" in sample.attrs:
        color = sample.attrs["color"]
        if isinstance(color, str) and color[0] == "k":
            color = eval(f"ROOT.{color}")
        color = int(color)
    else:
        color = None

    return h, sample.title, color


@click.command(context_settings=dict(max_content_width=120))
@click.option(
    "-s",
    "--sample-file",
    multiple=True,
    default=[DEFAULT_SAMPLE_FILE],
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path
    ),
    help="Sample file",
    show_default=True,
)
@click.option(
    "-p",
    "--period",
    default=PERIODS,
    type=click.Choice(PERIODS, case_sensitive=False),
    multiple=True,
    help="Datataking period [default: all]",
)
@click.option(
    "-n",
    "--name",
    metavar="NAME",
    default=DEFAULT_NAME,
    help="Name for output files",
    show_default=True,
)
@click.option(
    "-o",
    "--output",
    default=DEFAULT_OUTPUT,
    type=click.Path(file_okay=False, writable=True, path_type=pathlib.Path),
    help="Output directory",
    show_default=True,
)
@click.option(
    "--scale-bin",
    default=1,
    type=click.IntRange(0),
    help="Which bin for scale (0 all bins)",
)
@config.click_options()
@cache.click_options()
@utils.click_option_logging(log)
def main(
    sample_file: list[pathlib.Path],
    period: list[str],
    name: str,
    output: pathlib.Path,
    scale_bin: int,
):
    """W_pt Analysis."""
    cfg.load()

    output.mkdir(exist_ok=True)

    with cache.SamplesCache() as sc:
        for sf in sample_file:
            sc.load(sf)

            for p in period:
                log.info("Drawing plots for %s", p)

                output_path = output / f"{name}_{p}"

                inp_root_path = output_path.with_suffix(".root")
                if not inp_root_path.exists():
                    log.fatal("Input %s does not exists", inp_root_path)
                    return
                log.info("Reading histograms from %s", inp_root_path)
                inp_root = ROOT.TFile(str(inp_root_path), "READ")

                out_root_path = output_path.with_suffix(".plot01.root")
                log.info("Writing plots to %s", out_root_path)
                out_root = ROOT.TFile(str(out_root_path), "RECREATE")

                muon_sample = next(
                    sc.find(p, "SingleMuon", types=model.SampleType.DATA)
                )
                print(f"Muons: {muon_sample.name}")
                elec_sample = next(
                    sc.find(p, "SingleElectron", types=model.SampleType.DATA)
                )
                print(f"Electrons: {elec_sample.name}")
                wjet_sample = next(
                    sc.find(p, "WJets", types=model.SampleType.BACKGROUND)
                )
                print(f"WJets: {wjet_sample.name}")
                other_samples = []
                for sample in sc.list(p, types=model.SampleType.BACKGROUND):
                    if sample.name != "WJets":
                        other_samples.append(sample)
                        print(f"Other: {sample.name}")

                inp_root.Close()
                out_root.Close()


if __name__ == "__main__":
    main()
