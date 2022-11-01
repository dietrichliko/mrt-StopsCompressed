#!/usr/bin/env python
"""Drell Yan p_T Analysis."""
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
    / "lib/python3.10/site-packages/correctionlib"
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

DEFAULT_NAME = "dypt"

DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/DoubleLep_nanoNtuple_v8.yaml"
DEFAULT_HISTOS_FILE = BASE_DIR / "dypt_histos.yaml"


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


def init_muon_sf(period: str, file: str, muon_id: str):
    """Init muon scale factor."""
    try:
        ROOT.muon_sf
    except AttributeError:
        ROOT.gROOT.ProcessLine("std::unique_ptr<MuonSF> muon_sf;")

    ROOT.gROOT.ProcessLine(
        f'muon_sf = std::make_unique<MuonSF>("{period}", "{file}", "{muon_id}");'
    )


def init_elec_sf(period: str, file: str, working_point: str):
    """Init electroin scale factor."""
    try:
        ROOT.elec_sf
    except AttributeError:
        ROOT.gROOT.ProcessLine("std::unique_ptr<ElectronSF> elec_sf;")

    ROOT.gROOT.ProcessLine(
        "elec_sf = "
        f'std::make_unique<ElectronSF>("{period}", "{file}", "{working_point}");'
    )


class DYPTAnalysis(analysis.HistoAnalysis):
    """Dell Yan p_T analysis."""

    tight: bool
    lepton_sf: bool
    period: str
    muon_lumi: float
    elec_lumi: float
    muon_trigger: list[str]
    elec_trigger: list[str]
    muon_sf_path: str
    elec_sf_path: str

    def __init__(
        self,
        histo_file: pathlib.Path,
        output: pathlib.Path,
        small: bool,
        tight: bool,
        lepton_sf: bool,
        period: str,
        muon_attrs: dict[str, Any],
        elec_attrs: dict[str, Any],
    ) -> None:
        """Init w_pt analysis.

        Args:
            histo_file (Path): Yaml file with histogram definitions
            output (Path): Output directory
            small (bool): reduce sample size for debugging
            tight (bool): use tight muon definitions
            lepton_sf (bool): apply lepton scale factors
            period: str
            muon_attrs (dict[str, Any]): Attributes of muon sample
            elec_attrs (dict[str, Any]): attributes of electron sample
        """
        super().__init__(histo_file, output, small)
        self.tight = tight
        self.lepton_sf = lepton_sf
        self.period = period

        self.muon_trigger = muon_attrs["trigger"]
        self.muon_int_lumi = muon_attrs["integrated_luminosity"]
        self.muon_sf_path = (
            f"{BASE_DIR}/jsonpog-integration/POG" f"/MUO/{period[3:]}_UL/muon_Z.json.gz"
        )
        log.debug("Muon trigger: %s", " || ".join(self.muon_trigger))
        log.debug("Muon int. luminosity: %.2f", self.muon_int_lumi)
        log.debug("Muon sf path: %s", self.muon_sf_path)

        self.elec_trigger = elec_attrs["trigger"]
        self.elec_int_lumi = elec_attrs["integrated_luminosity"]
        self.elec_sf_path = (
            f"{BASE_DIR}/jsonpog-integration/POG"
            f"/EGM/{period[3:]}_UL/electron.json.gz"
        )
        log.debug("Electron trigger: %s", " || ".join(self.elec_trigger))
        log.debug("Electron inv lumi: %.2f", self.elec_int_lumi)
        log.debug("Electron sf path: %s", self.elec_sf_path)

    def define(self, sample: model.Sample, df: DataFrame) -> dict[str, DataFrame]:
        """Define dataframes.

        A number of different dataframes can be defined for various histograms.

        Args:
            sample (Sample): The sample to be analysed
            dataframe (RDataFrame): ROOT Dataframe of the sample

        Returns:
            dict[str, DataFrame]: Dict of dataframes
        """
        if self.tight:
            df = df.Define(
                "GoodMuon",
                "Muon_tightId && abs(Muon_eta) < 1.5 && Muon_pfRelIso03_all < 0.1 && Muon_pt > 15.",
            ).Define(
                "GoodElectron",
                "Electron_cutBased > 2 && abs(Electron_eta) < 1.5 && Electron_pfRelIso03_all < 0.1 && Electron_pt > 15.",  # noqa: B950
            )
            init_muon_sf(self.period, self.muon_sf_path, "TightID")
            init_elec_sf(self.period, self.elec_sf_path, "Medium")
        else:
            df = df.Define(
                "GoodMuon",
                "Muon_mediumId && abs(Muon_eta) < 1.5 && Muon_pfRelIso03_all < 0.1 && Muon_pt > 15.",
            ).Define(
                "GoodElectron",
                "Electron_cutBased > 1 && abs(Electron_eta) < 1.5 && Electron_pfRelIso03_all < 0.1 && Electron_pt > 15.",  # noqa: B950
            )
            init_muon_sf(self.period, self.muon_sf_path, "MediumID")
            init_elec_sf(self.period, self.elec_sf_path, "Loose")

        df = (
            df.Define("GoodMuon_pt", "Muon_pt[GoodMuon]")
            .Define("GoodMuon_phi", "Muon_phi[GoodMuon]")
            .Define("GoodMuon_eta", "Muon_eta[GoodMuon]")
            .Define("GoodMuon_charge", "Muon_charge[GoodMuon]")
            .Define("GoodMuon_mass", "Muon_mass[GoodMuon]")
            .Define("GoodElectron_pt", "Electron_pt[GoodElectron]")
            .Define("GoodElectron_phi", "Electron_phi[GoodElectron]")
            .Define("GoodElectron_eta", "Electron_eta[GoodElectron]")
            .Define("GoodElectron_charge", "Electron_charge[GoodElectron]")
            .Define("GoodElectron_mass", "Electron_mass[GoodElectron]")
        )

        # Event weights

        df_muon = filter_flags(df, self.muon_trigger)
        df_elec = filter_flags(df, self.elec_trigger)

        df_muon = (
            df_muon.Filter("GoodMuon_pt.size() == 2 && Max(GoodMuon_pt) > 40")
            .Filter("GoodMuon_charge[0] == - GoodMuon_charge[1]")
            .Define("lx1_idx", "ArgMax(GoodMuon_pt)")
            .Define("lx1_pt", "GoodMuon_pt[lx1_idx]")
            .Define("lx1_eta", "GoodMuon_eta[lx1_idx]")
            .Define("lx2_idx", "ArgMin(GoodMuon_pt)")
            .Define("lx2_pt", "GoodMuon_pt[lx2_idx]")
            .Define("lx2_eta", "GoodMuon_eta[lx2_idx]")
            .Define(
                "ll_mass",
                "InvariantMass(GoodMuon_pt,GoodMuon_eta,GoodMuon_phi,GoodMuon_mass)",
            )
            .Define("ll_pt", "TransverseMomentum(GoodMuon_pt,GoodMuon_phi)")
        )

        df_elec = (
            df_elec.Filter("GoodElectron_pt.size() == 2 && Max(GoodElectron_pt) > 40")
            .Filter("GoodElectron_charge[0] == - GoodElectron_charge[1]")
            .Define("lx1_idx", "ArgMax(GoodElectron_pt)")
            .Define("lx1_pt", "GoodElectron_pt[lx1_idx]")
            .Define("lx1_eta", "GoodElectron_eta[lx1_idx]")
            .Define("lx2_idx", "ArgMin(GoodElectron_pt)")
            .Define("lx2_pt", "GoodElectron_pt[lx2_idx]")
            .Define("lx2_eta", "GoodElectron_eta[lx2_idx]")
            .Define(
                "ll_mass",
                "InvariantMass(GoodElectron_pt,GoodElectron_eta,GoodElectron_phi,GoodElectron_mass)",
            )
            .Define("ll_pt", "TransverseMomentum(GoodElectron_pt,GoodElectron_phi)")
        )
        if sample.type == model.SampleType.DATA:
            muon_weight = "1"
            elec_weight = "1"
            df_muon = df_muon.Define("lx1_sf", "1.0").Define("lx2_sf", "1.0")
            df_elec = df_elec.Define("lx1_sf", "1.0").Define("lx2_sf", "1.0")
        else:
            if self.lepton_sf:
                df_muon = df_muon.Define(
                    "lx1_sf", "(*muon_sf)(lx1_pt, lx1_eta)"
                ).Define("lx2_sf", "(*muon_sf)(lx2_pt, lx2_eta)")
                df_elec = df_elec.Define(
                    "lx1_sf", "(*elec_sf)(lx1_pt, lx1_eta)"
                ).Define("lx2_sf", "(*elec_sf)(lx2_pt, lx2_eta)")
            else:
                df_muon = df_muon.Define("lx1_sf", "1.0").Define("lx2_sf", "1.0")
                df_elec = df_elec.Define("lx1_sf", "1.0").Define("lx2_sf", "1.0")

            weights = [
                "weight",
                "reweightPU",
                "reweightBTag_SF",
                "reweightL1Prefire",
                "lx1_sf",
                "lx2_sf",
                "{}",
            ]

            # if sample.name == "DYJetsToLL_M50_LO":
            #     log.debug("%s adding leptonSF", sample.name)
            #     weights.append("reweightLeptonSF")
            # else:
            #     log.debug("%s", sample.name)
            muon_weight = "*".join(weights).format(self.muon_int_lumi)
            elec_weight = "*".join(weights).format(self.elec_int_lumi)
        log.debug("Muon weight %s", muon_weight)
        log.debug("Electron weight %s", elec_weight)
        df_muon = df_muon.Define("the_weight", muon_weight)
        df_elec = df_elec.Define("the_weight", elec_weight)
        return {"muon": df_muon, "elec": df_elec}


class MyWorkerPlugin(analysis.WorkerPlugin):
    """Worker plugin for initialisation of workers."""

    def setup(self, worker: dd.Worker) -> None:
        """Setup ROOT on worker process."""
        super().setup(worker)
        ROOT.gROOT.ProcessLine(f'#include "{BASE_DIR}/dypt_inc.h"')
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
@click.option("--lepton-sf/--no-lepton-sf", default=True, help="Apply lepton sf")
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
    lepton_sf: bool,
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

                muon_sample_name = "DoubleMuon"
                if p == "Run2018":
                    elec_sample_name = "SingleElectron"
                else:
                    elec_sample_name = "DoubleEG"

                muon_sample = next(sc.find(p, muon_sample_name))
                elec_sample = next(sc.find(p, elec_sample_name))

                dypt_analysis = DYPTAnalysis(
                    histos_file,
                    output / f"{name}_{p}",
                    small,
                    tight,
                    lepton_sf,
                    p,
                    muon_sample.attrs,
                    elec_sample.attrs,
                )

                proc.run(sc, p, dypt_analysis, dataset)

            del proc  # shutdown dask cluster

        if plots:
            samples_plotter = plotter.SamplesPlotter(histos_file, output, name)
            for p in period:
                log.info("Drawing plots for %s", p)
                samples_plotter.plot(sc, p)


if __name__ == "__main__":
    main()
