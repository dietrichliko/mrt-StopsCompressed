#!/usr/bin/env python
"""Analyse the events weights."""
import logging
import pathlib
import sys
from mrtools import analysis
from mrtools import cache
from mrtools import config
from mrtools import model
from mrtools import utils

import click
import ROOT

# suppress FutureWarning from dask
if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore", FutureWarning, 20)

import dask.distributed as dd

DictValues = dict[str, int | float]

# base directory
BASE_DIR = pathlib.Path(__file__).absolute().parent
# default sample file to be read
DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/MetLepEnergy_nanoNtuple_v6.yaml"
# Run II
PERIODS = [
    "Run2016preVFP",
    "Run2016postVFP",
    "Run2017",
    "Run2018",
]
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
SMALL_MAX_FILES = 1

DF_NAMES = ("mu1", "mu2", "mu3", "el1", "el2", "el3")

DATA_SAMPLES = ["SingleMuon", "SingleElectron"]
BKG_SAMPLES = ["WJets", "TT", "T", "TTX", "DY", "DYINV", "QCD"]

ROOT.PyConfig.IgnoreCommandLineOptions = True
logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(name)s - %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.WARNING,
)
log = logging.getLogger("mrtools")
cfg = config.get()


class MyAnalysis(analysis.Analysis):
    """Analyse the events weights."""

    small: bool
    mu_trigger: list[str]
    mu_inv_lumi: float
    el_trigger: list[str]
    el_inv_lumi: float

    def __init__(
        self,
        mu_trigger: list[str],
        mu_inv_lumi: float,
        el_trigger: list[str],
        el_inv_lumi: float,
        small: bool = False,
    ) -> None:
        self.mu_trigger = mu_trigger
        self.mu_inv_lumi = mu_inv_lumi
        self.el_trigger = el_trigger
        self.el_inv_lumi = el_inv_lumi
        self.small = small

    def map(self, sample: model.Sample) -> DictValues:
        """Determine sum, min and max of event weights.

        Args:
            sample (model.Sample): The sample to analyse

        Returns:
            DictValues containing counters
        """
        log.info("Processing %s", sample)
        if self.small:
            chain = sample.chain(SMALL_MAX_FILES)
            nr_files = min(SMALL_MAX_FILES, len(sample))
        else:
            chain = sample.chain()
            nr_files = len(sample)

        # Temp workaround for cloudpickle
        # Not required for ROOT version >= 6.26
        # ROOT = __import__("ROOT")
        df_main = ROOT.RDataFrame(chain)

        if sample.type == model.SampleType.DATA:
            weight = "weight"
        else:
            weight = f"weight*{self.mu_inv_lumi}"

        log.debug("Weight: %s", weight)

        df_main = df_main.Define("the_weight", weight)
        cols = set(df_main.GetColumnNames())
        if bad_trg := ", ".join(t for t in self.mu_trigger if t not in cols):
            log.warning("Muon triggers missing: %s", bad_trg)

        if good_trg := " || ".join(t for t in self.mu_trigger if t in cols):
            log.debug("Muon tigger selection: %s", good_trg)
            df_mu1 = df_main.Filter(good_trg)
        else:
            log.error("No trigger selection for muons.")
            df_mu1 = df_main

        if bad_trg := ", ".join(t for t in self.el_trigger if t not in cols):
            log.warning("Electron triggers missing: %s", bad_trg)

        if good_trg := " || ".join(t for t in self.el_trigger if t in cols):
            log.debug("Electron tigger selection: %s", good_trg)
            df_el1 = df_main.Filter(good_trg)
        else:
            log.error("No trigger selection for electron.")

        df_mu2 = (
            df_mu1.Filter("HT>200. && met_pt>100.")
            .Define(
                "GoodMuon",
                "Muon_mediumId && abs(Muon_eta) < 1.5 && Muon_pfRelIso03_all < 0.1",
            )
            .Define("GoodMuon_pt", "Muon_pt[GoodMuon]")
        )
        df_el2 = (
            df_el1.Filter("HT>200. && met_pt>100.")
            .Define(
                "GoodElectron",
                "Electron_cutBased > 3 && abs(Electron_eta) < 1.5 && Electron_pfRelIso03_all < 0.1",
            )
            .Define("GoodElectron_pt", "Electron_pt[GoodElectron]")
        )

        df_mu3 = df_mu2.Filter("Sum(GoodMuon_pt>50.) > 0")
        df_el3 = df_el2.Filter("Sum(GoodElectron_pt>50.) > 0")

        df = {
            "mu1": df_mu1,
            "mu2": df_mu2,
            "mu3": df_mu3,
            "el1": df_el1,
            "el2": df_el2,
            "el3": df_el3,
        }

        results = {"nr_events": df_main.Count()}
        for n in DF_NAMES:
            results[f"{n}_nr_events"] = df[n].Count()
            results[f"{n}_sum_weights"] = df[n].Sum("the_weight")
            results[f"{n}_min_weights"] = df[n].Min("the_weight")
            results[f"{n}_max_weights"] = df[n].Max("the_weight")

        return {k: v.GetValue() for k, v in results.items()}

    def reduce(self, sample: model.SampleBase, results: list[DictValues]) -> DictValues:
        """Combine the results of various SampleGroups.

        Args:
            sample (model.SampleBase): The sample to combine.
            results (list[DictValues]): Results obtained by the children.

        Returns:
            DictValues are the combined results.
        """
        sum_results: DictValues = {}
        for r in results:
            for k, v in r.items():
                if k in sum_results:
                    if k.startswith("min_"):
                        sum_results[k] = min(sum_results[k], v)
                    elif k.startswith("max_"):
                        sum_results[k] = max(sum_results[k], v)
                    else:
                        sum_results[k] += v
                else:
                    sum_results[k] = v

        return sum_results

    def gather(self, future_to_sample: dict[dd.Future, model.SampleBase]) -> None:
        """Wait for all results.

        The default implentation is just waiting for the jobs to finish.

        Args:
            future_to_sample (dict[dd.Future, model.SampleBase]): Mapping of futures to samples
        """
        dd.wait(future_to_sample.keys())
        results: dict[str, DictValues] = {}
        for future, sample in future_to_sample.items():
            if sample.name in DATA_SAMPLES + BKG_SAMPLES:
                results[sample.name] = future.result()

        for name in DF_NAMES:
            data = "SingleMuon" if name.startswith("mu") else "SingleElectron"

            print(f"DF {name}")
            nr_events = results[data][f"{name}_nr_events"]
            sum_bkg = sum(results[bkg][f"{name}_sum_weights"] for bkg in BKG_SAMPLES)

            print(f"{data}: {nr_events}")
            print(f"Data/MC       : {nr_events/sum_bkg:5.2f}")
            for bkg in sorted(
                BKG_SAMPLES, key=lambda x: -results[x][f"{name}_sum_weights"]
            ):
                print(f"{bkg:<14}: {results[bkg][f'{name}_sum_weights']/sum_bkg:5.2f}")


@click.command
@click.option(
    "--config-file",
    default=None,
    type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path),
    help="Configuration file",
)
@click.option("--site", default="", help="Site name")
@click.option(
    "--samples-file",
    type=click.Path(exists=True, resolve_path=True, path_type=pathlib.Path),
    default=[DEFAULT_SAMPLE_FILE],
    multiple=True,
    help="Samples definitions",
    show_default=True,
)
@click.option(
    "--period",
    default="Run2016preVFP",
    type=click.Choice(PERIODS, case_sensitive=False),
    help="Datataking period",
    show_default=True,
)
@click.option(
    "--small/--no-small",
    default=False,
    help="Limit the number of files per sample.",
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
@config.option(cfg)
@utils.logging_option(log)
def main(
    samples_file: list[pathlib.Path],
    period: str,
    small: bool,
    root_threads: int,
    workers: int,
    max_workers: int,
    batch: bool,
    batch_memory: str,
    batch_walltime: str,
):
    """Verify the event weights."""
    cfg.load()

    ROOT.gROOT.SetBatch()

    with cache.SamplesCache() as sc:

        processor = analysis.Processor(
            root_threads,
            [],
            workers,
            max_workers,
            batch,
            batch_memory,
            batch_walltime,
        )

        for sf in samples_file:
            sc.load(sf)

        try:
            mu_sample = next(sc.find(period, "SingleMuon"))
            mu_trigger = mu_sample.attrs["trigger"]
            mu_inv_lumi = mu_sample.attrs["integrated_luminosity"]
            log.debug("Muon trigger: %s", " || ".join(mu_trigger))
            log.debug("Muon inv lumi: %.2f", mu_inv_lumi)
        except StopIteration:
            log.warning("No SingleMuon sample found.")
            mu_trigger = []
            mu_inv_lumi = 1

        try:
            el_sample = next(sc.find(period, "SingleElectron"))
            el_trigger = el_sample.attrs["trigger"]
            el_inv_lumi = el_sample.attrs["integrated_luminosity"]
            log.debug("Electron trigger: %s", " || ".join(el_trigger))
            log.debug("Electron inv lumi: %.2f", el_inv_lumi)
        except StopIteration:
            log.warning("No SingleElectron sample found.")
            el_trigger = []
            el_inv_lumi = 1

        my_analysis = MyAnalysis(
            mu_trigger, mu_inv_lumi, el_trigger, el_inv_lumi, small
        )

        processor.run(sc, period, my_analysis)


if __name__ == "__main__":
    main()
