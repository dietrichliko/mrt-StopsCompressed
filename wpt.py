#!/usr/bin/env python
"""W p_T Analysis."""
import logging
import os
import pathlib
from mrtools import analysis
from mrtools import cache
from mrtools import config
from mrtools import model
from mrtools import plotter
from mrtools import utils
from typing import Any

import click
import ROOT
import dask.distributed as dd

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
CORRECTIONLIB_DIR = (
    pathlib.Path(os.environ["CONDA_PREFIX"])
    / "lib/python3.11/site-packages/correctionlib"
)
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
DEFAULT_HISTOS_FILE = BASE_DIR / "wpt_histos.yaml"


def filter_flags(df: Any, flags: list[str]) -> Any:
    """DF Filter from flags.

    Check if flgas are present in the file before applying the filter.
    Not so clear, why this is necessary.

    Args:
        df (RDataFrame): ROOT dataframe
        flags (list[str]): List of flags
    """
    cols = df.GetColumnNames()
    if bad := ", ".join(t for t in flags if t not in cols):
        log.warning("Missing flags: %s", bad)

    if good := " || ".join(t for t in flags if t in cols):
        log.debug("Flag Selection: %s", good)
        return df.Filter(good)
    else:
        log.error("No valid flags.")
        return df


class WPTAnalysis(analysis.HistoAnalysis):
    """W_pt analysis."""

    tight: bool
    muon_lumi: float
    elec_lumi: float
    muon_trigger: list[str]
    elec_trigger: list[str]

    def __init__(
        self,
        histo_file: pathlib.Path,
        output: pathlib.Path,
        small: bool,
        tight: bool,
        muon_int_lumi: float,
        elec_int_lumi: float,
        muon_trigger: list[str],
        elec_trigger: list[str],
    ) -> None:
        """Init w_pt analysis.

        Args:
            histo_file (Path): Yaml file with histogram definitions
            output (Path): Output directory
            small (bool): reduce sample size for debugging
            tight (bool): use tight muon definitions
            muon_int_lumi (float): Integrated luminosity for muons sample
            elec_int_lumi (float): Integrated luminosity for electron sample
            muon_trigger (list[str]): Muon trigger selection
            elec_trigger (list[str]): Electron trigger selection
        """
        super().__init__(histo_file, output, small)
        self.tight = tight
        self.muon_int_lumi = muon_int_lumi
        self.elec_int_lumi = elec_int_lumi
        self.muon_trigger = muon_trigger
        self.elec_trigger = elec_trigger

    def define(self, sample: model.Sample, df: DataFrame) -> dict[str, DataFrame]:
        """Define dataframes.

        A number of different dataframes can be defined for various histograms.

        Args:
            sample (Sample): The sample to be analysed
            dataframe (RDataFrame): ROOT Dataframe of the sample

        Returns:
            dict[str, DataFrame]: Dict of dataframes
        """
        #       Event selection
        df = df.Filter("HT>200. && met_pt>100. && nBTag == 0")
        #       Lepton selection
        if self.tight:
            df = df.Define(
                "GoodMuon",
                "Muon_tightId && abs(Muon_eta) < 1.5 && Muon_pfRelIso03_all < 0.1",
            ).Define(
                "GoodElectron",
                "Electron_cutBased > 2 && abs(Electron_eta) < 1.5 && Electron_pfRelIso03_all < 0.1",  # noqa: B950
            )
        else:
            df = df.Define(
                "GoodMuon",
                "Muon_mediumId && abs(Muon_eta) < 1.5 && Muon_pfRelIso03_all < 0.1",
            ).Define(
                "GoodElectron",
                "Electron_cutBased > 1 && abs(Electron_eta) < 1.5 && Electron_pfRelIso03_all < 0.1",  # noqa: B950
            )

        df = (
            df.Define("GoodMuon_pt", "Muon_pt[GoodMuon]")
            .Define("GoodMuon_phi", "Muon_phi[GoodMuon]")
            .Define("GoodMuon_eta", "Muon_eta[GoodMuon]")
            .Define("GoodElectron_pt", "Electron_pt[GoodElectron]")
            .Define("GoodElectron_phi", "Electron_phi[GoodElectron]")
            .Define("GoodElectron_eta", "Electron_eta[GoodElectron]")
        )

        # Event weights

        df_muon = filter_flags(df, self.muon_trigger)
        df_elec = filter_flags(df, self.elec_trigger)

        if sample.type == model.SampleType.DATA:
            muon_weight = "1"
            elec_weight = "1"
        else:
            weights = [
                "weight",
                "reweightPU",
                "reweightBTag_SF",
                "reweightL1Prefire",
                "reweightLeptonSF",
                "{}",
            ]
            muon_weight = "*".join(weights).format(self.muon_int_lumi)
            elec_weight = "*".join(weights).format(self.elec_int_lumi)
        log.debug("Muon weight %s", muon_weight)
        log.debug("Electron weight %s", elec_weight)
        df_muon = df_muon.Define("the_weight", muon_weight)
        df_elec = df_elec.Define("the_weight", elec_weight)

        df_muon = (
            df_muon.Filter("Sum(GoodMuon_pt > 50.) > 0")
            .Filter("Sum(GoodElectron_pt > 50.) == 0")
            .Define("ll_idx", "ArgMax(GoodMuon_pt)")
            .Define("ll_pt", "GoodMuon_pt[ll_idx]")
            .Define("ll_phi", "GoodMuon_phi[ll_idx]")
            .Define("ll_eta", "GoodMuon_eta[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )

        df_elec = (
            df_elec.Filter("Sum(GoodElectron_pt > 50.) > 0")
            .Filter("Sum(GoodMuon_pt > 50.) == 0")
            .Define("ll_idx", "ArgMax(GoodElectron_pt)")
            .Define("ll_pt", "GoodElectron_pt[ll_idx]")
            .Define("ll_phi", "GoodElectron_phi[ll_idx]")
            .Define("ll_eta", "GoodElectron_eta[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )
        return {"muon": df_muon, "elec": df_elec}


class MyWorkerPlugin(analysis.WorkerPlugin):
    """Worker plugin for initialisation of workers."""

    def setup(self, worker: dd.Worker) -> None:
        """Setup ROOT on worker process."""
        super().setup(worker)
        ROOT.gROOT.ProcessLine(f'#include "{BASE_DIR}/wpt_inc.h"')
        ROOT.gROOT.ProcessLine(f".include {CORRECTIONLIB_DIR}/include")
        ROOT.gSystem.Load(f"{CORRECTIONLIB_DIR}/lib/libcorrectionlib.so")
        ROOT.gROOT.ProcessLine(f'#include "{BASE_DIR}/leptonsf_inc.h"')

@click.command(context_settings=dict(max_content_width=120))
@click.argument("dataset", nargs=-1)
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
    "-f",
    "--histos-file",
    type=click.Path(exists=True, resolve_path=True),
    default=DEFAULT_HISTOS_FILE,
    help="Histogram definitions",
    show_default=True,
)
@click.option("--small/--no-small", default=False, help="Reduce sample size.")
@click.option("--histos/--no-histos", default=True, help="Fill histograms.")
@click.option("--plots/--no-plots", default=True, help="Make plots from histograms.")
@click.option("--tight/--no-tight", default=True, help="Tight lepton selection.")
@config.click_options()
@cache.click_options()
@analysis.click_options()
@utils.click_option_logging(log)
def main(
    dataset: list[str],
    sample_file: list[pathlib.Path],
    period: list[str],
    name: str,
    output: pathlib.Path,
    histos_file: pathlib.Path,
    small: bool,
    histos: bool,
    plots: bool,
    tight: bool,
):
    """W_pt Analysis."""
    cfg.load()

    output.mkdir(exist_ok=True)

    with cache.SamplesCache() as sc:
        for sf in sample_file:
            sc.load(sf)

        if histos:
            proc = analysis.Processor(MyWorkerPlugin())
            for p in period:
                log.info("Filling histos for %s", p)

                muon_sample = next(sc.find(p, "SingleMuon"))
                print(f"Muon Sample {muon_sample}")
                muon_trigger = muon_sample.attrs["trigger"]
                muon_int_lumi = muon_sample.attrs["integrated_luminosity"]
                log.debug("Muon trigger: %s", " || ".join(muon_trigger))
                log.debug("Muon int. luminosity: %.2f", muon_int_lumi)

                elec_sample = next(sc.find(p, "SingleElectron"))
                elec_trigger = elec_sample.attrs["trigger"]
                elec_int_lumi = elec_sample.attrs["integrated_luminosity"]
                log.debug("Electron trigger: %s", " || ".join(elec_trigger))
                log.debug("Electron inv lumi: %.2f", elec_int_lumi)

                wpt_analysis = WPTAnalysis(
                    histos_file,
                    output / f"{name}_{p}",
                    small,
                    tight,
                    muon_int_lumi,
                    elec_int_lumi,
                    muon_trigger,
                    elec_trigger,
                )
                proc.run(sc, p, wpt_analysis, dataset)

            del proc  # shutdown dask cluster

        if plots:
            samples_plotter = plotter.SamplesPlotter(histos_file, output, name)
            for p in period:
                log.info("Drawing plots for %s", p)
                samples_plotter.plot(sc, p)


if __name__ == "__main__":
    main()
