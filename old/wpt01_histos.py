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

DEFAULT_OUTPUT = pathlib.Path("/scratch-cbe/users", os.environ["USER"], "WPT")
DEFAULT_NAME = "wpt01_{period}"

DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/MetLepEnergy_nanoNtuple_v6.yaml"
DEFAULT_HISTOS_FILE = BASE_DIR / "wpt01.histos.yaml"

ALL_WEIGHTS = [
    "weight",
    "reweightPU",
    "reweightBTag_SF",
    "reweightL1Prefire",
    "reweightLeptonSF",
    "{}",
]


def filter_flags(df: Any, flags: list[str]) -> Any:
    """DF Filter fron flags."""
    cols = df.GetColumnNames()
    if bad := ", ".join(t for t in flags if t not in cols):
        log.warning("Missing flags: %s", bad)

    if good := " || ".join(t for t in flags if t in cols):
        log.debug("Flag Selection: %s", good)
        return df.Filter(good)
    else:
        log.error("No valid flags.")
        return df


class WPtAnalysis(analysis.HistoAnalysis):
    """W_pt analysis."""

    reweight: bool
    tight: bool
    trigger: bool
    mu_lumi: float
    el_lumi: float
    mu_trigger: list[str]
    el_trigger: list[str]
    btag: bool

    def __init__(
        self,
        histo_file: pathlib.Path,
        output: pathlib.Path,
        small: bool,
        reweight: bool,
        tight: bool,
        trigger: bool,
        mu_lumi: float,
        el_lumi: float,
        mu_trigger: list[str],
        el_trigger: list[str],
        btag: bool,
    ) -> None:
        super().__init__(histo_file, output, small)

        self.reweight = reweight
        self.tight = tight
        self.trigger = trigger
        self.mu_lumi = mu_lumi
        self.el_lumi = el_lumi
        self.mu_trigger = mu_trigger
        self.el_trigger = el_trigger
        self.btag = btag

    def define(self, sample: model.Sample, df: DataFrame) -> dict[str, DataFrame]:

        df = df.Filter("HT>200. && met_pt>100.")
        if self.btag:
            df = df.Filter("nBTag == 0")

        # Good Leptons
        if self.tight:
            df = df.Define(
                "GoodMuon",
                "Muon_tightId && abs(Muon_eta) < 1.5 && Muon_pfRelIso03_all < 0.1",
            ).Define(
                "GoodElectron",
                "Electron_cutBased > 3 && abs(Electron_eta) < 1.5 && Electron_pfRelIso03_all < 0.1",  # noqa: B950
            )
        else:
            df = df.Define(
                "GoodMuon",
                "Muon_mediumId && abs(Muon_eta) < 1.5 && Muon_pfRelIso03_all < 0.1",
            ).Define(
                "GoodElectron",
                "Electron_cutBased > 2 && abs(Electron_eta) < 1.5 && Electron_pfRelIso03_all < 0.1",  # noqa: B950
            )

        # Leptons with varuious criteria
        df = (
            df.Define("MediumMuon_pt", "Muon_pt[Muon_mediumId]")
            .Define("MediumMuon_phi", "Muon_phi[Muon_mediumId]")
            .Define("MediumMuon_eta", "Muon_eta[Muon_mediumId]")
            .Define("TightMuon_pt", "Muon_pt[Muon_tightId]")
            .Define("TightMuon_phi", "Muon_phi[Muon_tightId]")
            .Define("TightMuon_eta", "Muon_eta[Muon_tightId]")
            .Define("GoodMuon_pt", "Muon_pt[GoodMuon]")
            .Define("GoodMuon_phi", "Muon_phi[GoodMuon]")
            .Define("GoodMuon_eta", "Muon_eta[GoodMuon]")
            .Define("MediumElectron_pt", "Electron_pt[Electron_cutBased > 2]")
            .Define("MediumElectron_phi", "Electron_phi[Electron_cutBased > 2]")
            .Define("MediumElectron_eta", "Electron_eta[Electron_cutBased > 2]")
            .Define("TightElectron_pt", "Electron_pt[Electron_cutBased > 3]")
            .Define("TightElectron_phi", "Electron_phi[Electron_cutBased > 3]")
            .Define("TightElectron_eta", "Electron_eta[Electron_cutBased > 3]")
            .Define("GoodElectron_pt", "Electron_pt[GoodElectron]")
            .Define("GoodElectron_phi", "Electron_phi[GoodElectron]")
            .Define("GoodElectron_eta", "Electron_eta[GoodElectron]")
        )

        # Lepton genFlav
        if sample.type == model.SampleType.DATA:
            df = (
                df.Define(
                    "MediumMuon_genPartFlav", "ROOT::RVec(MediumMuon_pt.size(),-1)"
                )
                .Define(
                    "MediumElectron_genPartFlav",
                    "ROOT::RVec(MediumElectron_pt.size(),-1)",
                )
                .Define("TightMuon_genPartFlav", "ROOT::RVec(TightMuon_pt.size(),-1)")
                .Define(
                    "TightElectron_genPartFlav",
                    "ROOT::RVec(TightElectron_pt.size(),-1)",
                )
                .Define("GoodMuon_genPartFlav", "ROOT::RVec(GoodMuon_pt.size(),-1)")
                .Define(
                    "GoodElectron_genPartFlav", "ROOT::RVec(GoodElectron_pt.size(),-1)"
                )
            )
        else:
            df = (
                df.Define("MediumMuon_genPartFlav", "Muon_genPartFlav[Muon_mediumId]")
                .Define(
                    "MediumElectron_genPartFlav",
                    "Electron_genPartFlav[Electron_cutBased > 2]",
                )
                .Define("TightMuon_genPartFlav", "Muon_genPartFlav[Muon_tightId]")
                .Define(
                    "TightElectron_genPartFlav",
                    "Electron_genPartFlav[Electron_cutBased > 3]",
                )
                .Define("GoodMuon_genPartFlav", "Muon_genPartFlav[GoodMuon]")
                .Define(
                    "GoodElectron_genPartFlav", "Electron_genPartFlav[GoodElectron]"
                )
            )

        # Event weights
        if sample.type == model.SampleType.DATA:
            mu_weight = "1"
            el_weight = "1"
        else:
            if self.reweight:
                weights = "*".join(ALL_WEIGHTS)
            else:
                weights = "weight*{}"
            mu_weight = weights.format(self.mu_lumi)
            el_weight = weights.format(self.el_lumi)

        # log.debug("Muon weight    : %s", mu_weight)
        # log.debug("Electron weight: %s", el_weight)
        df_mu0 = df.Define("the_weight", mu_weight)
        df_el0 = df.Define("the_weight", el_weight)

        if self.trigger:
            df_mu0 = filter_flags(df_mu0, self.mu_trigger)
            df_el0 = filter_flags(df_el0, self.el_trigger)

        # Events with leading muons
        df_mu1 = (
            df_mu0.Filter("Sum(MediumMuon_pt > 30.) > 0")
            .Define("ll_idx", "ArgMax(MediumMuon_pt)")
            .Define("ll_pt", "MediumMuon_pt[ll_idx]")
            .Define("ll_phi", "MediumMuon_phi[ll_idx]")
            .Define("ll_eta", "MediumMuon_eta[ll_idx]")
            .Define("ll_genFlav", "MediumMuon_genPartFlav[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )

        df_mu2 = (
            df_mu0.Filter("Sum(TightMuon_pt > 30.) > 0")
            .Define("ll_idx", "ArgMax(TightMuon_pt)")
            .Define("ll_pt", "TightMuon_pt[ll_idx]")
            .Define("ll_phi", "TightMuon_phi[ll_idx]")
            .Define("ll_eta", "TightMuon_eta[ll_idx]")
            .Define("ll_genFlav", "TightMuon_genPartFlav[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )

        df_mu3 = (
            df_mu0.Filter("Sum(GoodMuon_pt > 50.) > 0")
            .Filter("Sum(GoodElectron_pt > 50.) == 0")
            .Define("ll_idx", "ArgMax(GoodMuon_pt)")
            .Define("ll_pt", "GoodMuon_pt[ll_idx]")
            .Define("ll_phi", "GoodMuon_phi[ll_idx]")
            .Define("ll_eta", "GoodMuon_eta[ll_idx]")
            .Define("ll_genFlav", "GoodMuon_genPartFlav[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )

        # Events with leading electrons
        df_el1 = (
            df_el0.Filter("Sum(MediumElectron_pt > 30.) > 0")
            .Define("ll_idx", "ArgMax(MediumElectron_pt)")
            .Define("ll_pt", "MediumElectron_pt[ll_idx]")
            .Define("ll_phi", "MediumElectron_phi[ll_idx]")
            .Define("ll_eta", "MediumElectron_eta[ll_idx]")
            .Define("ll_genFlav", "MediumElectron_genPartFlav[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )

        df_el2 = (
            df_el0.Filter("Sum(TightElectron_pt > 30.) > 0")
            .Define("ll_idx", "ArgMax(TightElectron_pt)")
            .Define("ll_pt", "TightElectron_pt[ll_idx]")
            .Define("ll_phi", "TightElectron_phi[ll_idx]")
            .Define("ll_eta", "TightElectron_eta[ll_idx]")
            .Define("ll_genFlav", "TightElectron_genPartFlav[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )

        df_el3 = (
            df_el0.Filter("Sum(GoodElectron_pt > 50.) > 0")
            .Filter("Sum(GoodMuon_pt > 50.) == 0")
            .Define("ll_idx", "ArgMax(GoodElectron_pt)")
            .Define("ll_pt", "GoodElectron_pt[ll_idx]")
            .Define("ll_phi", "GoodElectron_phi[ll_idx]")
            .Define("ll_eta", "GoodElectron_eta[ll_idx]")
            .Define("ll_genFlav", "GoodElectron_genPartFlav[ll_idx]")
            .Define("LT", "ll_pt + met_pt")
            .Define("W_pt", "pt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
            .Define("W_mt", "mt_lep_met(ll_pt, ll_phi, met_pt, met_phi)")
        )

        return {
            "df_mu0": df_mu0,
            "df_mu1": df_mu1,
            "df_mu2": df_mu2,
            "df_mu3": df_mu3,
            "df_el0": df_el0,
            "df_el1": df_el1,
            "df_el2": df_el2,
            "df_el3": df_el3,
        }


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
@click.option(
    "--reweight/--no-reweight",
    default=False,
    help="Perform reweighting for various effects.",
    show_default=True,
)
@click.option(
    "--tight/--no-tight",
    default=False,
    help="Tight lepton identification.",
    show_default=True,
)
@click.option(
    "--trigger/--no-trigger",
    default=True,
    help="Perform trigger selection.",
    show_default=True,
)
@click.option(
    "--btag/--no-btag",
    default=True,
    help="Perform anti b tag.",
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
    reweight: bool,
    tight: bool,
    trigger: bool,
    btag: bool,
):
    """Run example01."""
    cfg.load(config_file, site)

    ROOT.gROOT.SetBatch()

    base_dir = pathlib.Path(__file__).absolute().parent

    output.mkdir(parents=True, exist_ok=True)

    with cache.SamplesCache() as sc:
        for s in samples_file:
            sc.load(s)

        proc = analysis.Processor(
            root_threads,
            [f"{base_dir}/wpt01_inc.h"],
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

            wpt_analysis = WPtAnalysis(
                histos_file,
                output / name.format(period=p),
                small,
                reweight,
                tight,
                trigger,
                mu_lumi,
                el_lumi,
                mu_trg,
                el_trg,
                btag,
            )
            proc.run(sc, p, wpt_analysis)


if __name__ == "__main__":
    main()
