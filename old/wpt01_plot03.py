#!/usr/bin/env python
"""Modern ROOT Tools example01."""
import itertools
import json
import logging
import os
import pathlib
import sys
from array import array
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

DY_BINS = [0.0, 50.0, 100.0, 150.0, 200.0, 300.0, 400.0, 600.0, 1200.0]
DY_VALS = [1.0, 1.052, 1.179, 1.150, 1.057, 1.00, 0.912, 0.783]
DY_ERRS = [0.0, 0.001, 0.002, 0.003, 0.004, 0.008, 0.012, 0.023]

DY_X = [25.0, 75.0, 125.0, 175.0, 250.0, 350.0, 500.0, 900.0]
DY_Y = [1.0, 1.052, 1.179, 1.150, 1.057, 1.00, 0.912, 0.783]
DY_XEL = [25.0, 25.0, 25.0, 25.0, 50.0, 50.0, 100.0, 300.0]
DY_XEH = [50.0, 25.0, 25.0, 25.0, 50.0, 50.0, 100.0, 300.0]
DY_YEL = len(DY_X) * [1.0]
DY_YEH = []
for i, y in enumerate(DY_Y):
    DY_Y[i] = 0.94 * y
    DY_YEH.append(DY_Y[i] ** 2)

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

BKG_SAMPLES = ("WJets", "TT", "T", "TTX", "DY", "DYINV", "QCD")

DEFAULT_OUTPUT = pathlib.Path("/scratch-cbe/users", os.environ["USER"], "WPT")
DEFAULT_NAME = "wpt01_{period}"

DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/MetLepEnergy_nanoNtuple_v6.yaml"
DEFAULT_HISTOS_FILE = BASE_DIR / "wpt01.histos.yaml"


def get_s(
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
    output: pathlib.Path,
):
    """Run example01."""
    cfg.load(config_file, site)

    ROOT.gROOT.SetBatch()
    plotter.tdr_style()

    h_dy = ROOT.TH1F("dy_scale", "", len(DY_BINS) - 1, array("d", DY_BINS))
    for i, (v, e) in enumerate(zip(DY_VALS, DY_ERRS)):
        h_dy.SetBinContent(i + 1, v)
        h_dy.SetBinError(i + 1, e)

    all_div = {}
    for p in period:
        output_path = output / name.format(period=p)
        inp_root_path = output_path.with_suffix(".root")
        if not inp_root_path.exists():
            log.fatal("Input %s does not exists", inp_root_path)
            sys.exit()
        log.info("Reading histograms from %s", inp_root_path)
        inp_root = ROOT.TFile(str(inp_root_path), "READ")

        with open(output_path.with_suffix(".json"), "r") as input_json:
            stat = json.load(input_json)

        (output_path / "03").mkdir(parents=True, exist_ok=True)

        for df, var, norm in itertools.product(
            ["mu3", "el3"], ["W_pt", "W_pt_var", "W_pt_varY", "W_pt_varX"], [0, 1, 2, 3]
        ):
            log.debug("Histogram %s_%s", df, var)
            s_dat = "SingleMuon" if df == "mu3" else "SingleElectron"
            h_dat = inp_root.Get(f"{s_dat}/{df}_{var}")
            h_bkg = {s: inp_root.Get(f"{s}/{df}_{var}") for s in BKG_SAMPLES}

            if norm == 0:
                scale = 1.0
                log.info("Fixed Scale %.3f", scale)
            elif norm == 1:
                n_dat = stat[s_dat][f"df_{df}_nr_events"]
                n_bkg = sum(stat[s][f"df_{df}_sum_weights"] for s in BKG_SAMPLES)
                scale = n_dat / n_bkg
                log.info(
                    "Norm events - Data %d - Bkg %.1f - Scale %.3f",
                    n_dat,
                    n_bkg,
                    scale,
                )
            elif norm == 2:
                n_dat = h_dat.Integral()
                n_bkg = sum(h.Integral() for h in h_bkg.values())
                scale = n_dat / n_bkg
                log.info(
                    "Norm integral - Data %d - Bkg %.1f - Scale %.3f",
                    n_dat,
                    n_bkg,
                    scale,
                )
            elif norm == 3:
                n_dat = h_dat.GetBinContent(3)
                n_bkg = sum(h.GetBinContent(3) for h in h_bkg.values())
                scale = n_dat / n_bkg
                log.info(
                    "Norm bin 1 - Data %d - Bkg %.1f - Scale %.3f",
                    n_dat,
                    n_bkg,
                    scale,
                )

            hstack_bkg = ROOT.THStack("sum_bkg", "")
            hsum_bkg = h_dat.Clone()
            hsum_bkg.Reset()
            for h in h_bkg.values():
                h.Scale(scale)
                hstack_bkg.Add(h)
                hsum_bkg.Add(h)

            h_ratio = h_dat / hsum_bkg

            c1 = ROOT.TCanvas()
            c1.Divide(1, 2, 0, 0)
            c1.cd(1)
            h_dat.SetMarkerStyle(20)
            h_dat.SetMarkerSize(0.5)
            max = h_dat.GetMaximum()
            hstack_bkg.SetMaximum(max * 1.2)
            hstack_bkg.Draw("hist")
            h_dat.Draw("ep same")

            c1.cd(2)
            h_ratio.SetMarkerStyle(20)
            h_ratio.SetMarkerSize(0.5)
            h_ratio.Draw()

            save = ROOT.gErrorIgnoreLevel
            ROOT.gErrorIgnoreLevel = ROOT.kWarning
            c1.SaveAs(f"{output_path}/03/{df}_{var}_{norm}_stack.png")
            ROOT.gErrorIgnoreLevel = save

            for n, h in h_bkg.items():
                if n != "WJets":
                    h_dat.Add(h, -1.0)

            h_div = h_dat.Clone()
            h_div.Reset()
            h_div.Divide(h_dat, h_bkg["WJets"])

            c1 = ROOT.TCanvas()
            h_div.SetMarkerStyle(20)
            h_div.SetMarkerSize(0.5)
            h_div.Draw("ep")

            if norm == 2:
                all_div[f"{df}_{p}_{var}"] = h_div.Clone(f"{df}_{p}_{var}")

            save = ROOT.gErrorIgnoreLevel
            ROOT.gErrorIgnoreLevel = ROOT.kWarning
            c1.SaveAs(f"{output_path}/03/{df}_{var}_{norm}_div.png")
            ROOT.gErrorIgnoreLevel = save

        for var in ("W_pt", "W_pt_var", "W_pt_varY", "W_pt_varX"):
            h_mu = all_div[f"mu3_{p}_{var}"].Clone()
            h_el = all_div[f"el3_{p}_{var}"].Clone()

            c0 = ROOT.TCanvas()
            c0.SetGrid()
            h_mu.SetMinimum(0.5)
            h_mu.SetMaximum(1.5)
            h_mu.SetMarkerStyle(22)
            h_mu.SetMarkerSize(1.0)
            h_mu.SetMarkerColor(ROOT.kYellow)
            h_mu.Draw("EP")
#            h_mu.Draw("CHIST SAME")

            h_el.SetMarkerStyle(21)
            h_el.SetMarkerSize(1.0)
            h_mu.SetMarkerColor(ROOT.kGreen)
            h_el.Draw("EP SAME")
#            h_el.Draw("CHIST SAME")

            # dy = ROOT.TGraphAsymmErrors(
            #     len(DY_X),
            #     array("d", DY_X),
            #     array("d", DY_Y),
            #     array("d", DY_XEL),
            #     array("d", DY_XEH),
            #     array("d", DY_YEL),
            #     array("d", DY_YEH),
            # )
            # dy.SetMarkerColor(ROOT.kRed)
            # dy.SetFillColorAlpha(ROOT.kRed, 0.35)
            # dy.SetMarkerStyle(21)
            # dy.Draw("ALP SAME")
            #            dy.Draw("E4 SAME")

            h_dy.SetMarkerStyle(22)
            h_dy.SetMarkerSize(1.0)
            h_dy.SetMarkerColor(ROOT.kRed)
            h_dy.Draw("CHIST SAME")
            h_dy.Draw("EP SAME")

            save = ROOT.gErrorIgnoreLevel
            ROOT.gErrorIgnoreLevel = ROOT.kWarning
            c0.SaveAs(f"{output_path}/03/{var}_all.png")
            ROOT.gErrorIgnoreLevel = save

    # for var in ("W_pt", "W_pt_var", "W_pt_varY", "W_pt_varX"):

    #     c0 = ROOT.TCanvas()

    #     for i, p in enumerate(period):
    #         print(f"mu3_{p}_{var}")
    #         h_mu = all_div[f"mu3_{p}_{var}"].Clone()
    #         print(f"el3_{p}_{var}")
    #         h_el = all_div[f"el3_{p}_{var}"].Clone()
    #         h_mu.SetMinimum(0.1)
    #         h_mu.SetMaximum(1.5)
    #         h_mu.SetMarkerStyle(20 + i)
    #         h_mu.SetMarkerSize(0.5)
    #         if i == 0:
    #             h_mu.Draw("ep")
    #         else:
    #             h_mu.Draw("ep same")

    #         h_el.SetMinimum(0.1)
    #         h_el.SetMaximum(1.5)
    #         h_el.SetMarkerStyle(24 + i)
    #         h_el.SetMarkerSize(0.5)
    #         h_el.Draw("ep same")

    #     save = ROOT.gErrorIgnoreLevel
    #     ROOT.gErrorIgnoreLevel = ROOT.kWarning
    #     c0.SaveAs(f"{output}/{var}_all.png")
    #     ROOT.gErrorIgnoreLevel = save


if __name__ == "__main__":
    main()
