#!/usr/bin/env python
"""Modern ROOT Tools example01."""
import logging
import os
import pathlib
from mrtools import analysis
from mrtools import cache
from mrtools import config
from mrtools import model
from mrtools import utils
from typing import Any
from typing import Iterator

import click
import ROOT

DataFrame = Any

ROOT.PyConfig.IgnoreCommandLineOptions = True

logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(name)s - %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.WARNING,
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

DEFAULT_OUTPUT = pathlib.Path("/scratch-cbe/users", os.environ["USER"], "DY")
DEFAULT_NAME = "dy01_{period}"

DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/MetLepEnergy_nanoNtuple_v6.yaml"
DEFAULT_HISTOS_FILE = BASE_DIR / "dy01.histos.yaml"

class DYAnalysis(analysis.HistoAnalysis):
    """DY analysis."""

    mu_lumi: float
    el_lumi: float
    mu_trigger: list[str]
    el_trigger: list[str]

    def __init__(
        self,
        histo_file: pathlib.Path,
        output: pathlib.Path,
        small: bool,
        mu_lumi: float,
        el_lumi: float,
        mu_trigger: list[str],
        el_trigger: list[str],
    ) -> None:
        super().__init__(histo_file, output, small)


        self.mu_lumi = mu_lumi
        self.el_lumi = el_lumi
        self.mu_trigger = mu_trigger
        self.el_trigger = el_trigger

    def define(self, sample: model.Sample, df: DataFrame) -> dict[str, DataFrame]:


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
    help="Name for output files",
    show_default=True,
)
@click.option(
    "--period",
    default=PERIODS,
    type=click.Choice(PERIODS, case_sensitive=False),
    multiple=True,
    help="Datataking period (dafault: all)",
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
    "--root-threads",
    type=click.IntRange(0, None),
    default=0,
    help="Number of root threads",
    show_default=True,
)
@click.option(
    "--output",
    default=DEFAULT_OUTPUT,
    type=click.Path(file_okay=False, writable=True, path_type=pathlib.Path),
    help="Output directory",
    show_default=True,
)
@click.option(
    "--workers",
    metavar="WORKERS",
    default=4,
    type=int,
    help="Worker processes",
    show_default=True,
)
@click.option(
    "--max-workers",
    metavar="MAX",
    type=int,
    default=0,
    help="Adaptive scaling with MAX workers",
)
@click.option(
    "--batch/--no-batch",
    default=False,
    help="Submit job to the batch system",
    show_default=True,
)
@click.option(
    "--batch-walltime",
    metavar="TIME",
    default="",
    help="Walltime for batch workers",
)
@click.option(
    "--batch-memory",
    metavar="MEMORY",
    default="",
    help="Memory for batch workers",
)
@click.option(
    "--small/--no-small",
    default=False,
    help="Limit the number of files per sample.",
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
    root_threads: int,
    workers: int,
    max_workers: int,
    batch: bool,
    batch_memory: str,
    batch_walltime: str,
    output: pathlib.Path,
    small: bool,
):
    """Stup Drell-Yan sample for ISR."""
    cfg.load(config_file, site)

    ROOT.gROOT.SetBatch()

    output.mkdir(parents=True, exist_ok=True)

    with cache.SamplesCache() as sc:
        for s in samples_file:
            sc.load(s)

        proc = analysis.Processor(
            root_threads,
            [f"{BASE_DIR}/wpt01_inc.h"],
            workers,
            max_workers,
            batch,
            batch_memory,
            batch_walltime,
        )

        for p in period:
            log.info("Processing period %s", p)

            mu_sample = sc.get(p, "SingleMuon")
            mu_trg = mu_sample.attrs["trigger"]
            mu_lumi = mu_sample.attrs["integrated_luminosity"]
            log.debug("Muon trigger: %s", " || ".join(mu_trg))
            log.debug("Muon inv lumi: %.2f", mu_lumi)

            el_sample = sc.get(p, "SingleElectron")
            el_trg = el_sample.attrs["trigger"]
            el_lumi = el_sample.attrs["integrated_luminosity"]
            log.debug("Electron trigger: %s", " || ".join(el_trg))
            log.debug("Electron inv lumi: %.2f", el_lumi)

            dy_analysis = DYAnalysis(
                histos_file,
                output / name.format(period=p),
                small,
                mu_lumi,
                el_lumi,
                mu_trg,
                el_trg,
            )
            proc.run(sc, p, dy_analysis)
    



if __name__ == '__main__':
    main()
