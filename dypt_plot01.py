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

DEFAULT_NAME = "dypt"

DEFAULT_SAMPLE_FILE = BASE_DIR / "samples/DoubleLep_nanoNtuple_v8.yaml"

DATA_SAMPLES = {
    "Run2016preVFP": {
        "muon": "DoubleMuon",
        "elec": "DoubleEG",
    },
    "Run2016postVFP": {
        "muon": "DoubleMuon",
        "elec": "DoubleEG",
    },
    "Run2017": {
        "muon": "DoubleMuon",
        "elec": "DoubleEG",
    },
    "Run2018": {
        "muon": "DoubleMuon",
        "elec": "SingleElectron",
    },
}


ISR_CORRECTIONS = [
    # 1.0,
    # 1.052,
    # 1.179,
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
@config.click_options()
@cache.click_options()
@utils.click_option_logging(log)
def main(
    sample_file: list[pathlib.Path], period: list[str], name: str, output: pathlib.Path
):

    """W_pt Analysis."""
    cfg.load()

    output.mkdir(exist_ok=True)

    int_lumi: dict[str, float] = {}
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

                for df in ["muon", "elec"]:

                    samples_dat = list(
                        sc.find(p, DATA_SAMPLES[p][df], types=model.SampleType.DATA)
                    )
                    samples_bkg = list(sc.list(p, types=model.SampleType.BACKGROUND))

                    int_lumi[p] = float(samples_dat[0].attrs["integrated_luminosity"])
                    hname = f"{df}_ll_pt_2"

                    histos_dat = [get_histo(inp_root, hname, s) for s in samples_dat]
                    histos_bkg = [get_histo(inp_root, hname, s) for s in samples_bkg]

                    sum_dat = sum(h[0].Integral() for h in histos_dat)
                    sum_bkg = sum(h[0].Integral() for h in histos_bkg)

                    plotter.stackplot(
                        output_path / f"plot01_{hname}_lin_1.png",
                        histos_dat,
                        histos_bkg,
                        [],
                        logy=False,
                        scale=sum_dat / sum_bkg,
                    )

                    # histos_dat = [get_histo(inp_root, hname, s) for s in samples_dat]
                    # histos_bkg = [get_histo(inp_root, hname, s) for s in samples_bkg]

                    plotter.stackplot(
                        output_path / f"plot01_{hname}_log_1.png",
                        histos_dat,
                        histos_bkg,
                        [],
                        logy=True,
                        scale=sum_dat / sum_bkg,
                    )

                    # histos_dat = [get_histo(inp_root, hname, s) for s in samples_dat]
                    # histos_bkg = [get_histo(inp_root, hname, s) for s in samples_bkg]

                    sum_dat = sum(h[0].GetBinContent(1) for h in histos_dat)
                    sum_bkg = sum(h[0].GetBinContent(1) for h in histos_bkg)

                    plotter.stackplot(
                        output_path / f"plot01_{hname}_lin_2.png",
                        histos_dat,
                        histos_bkg,
                        [],
                        logy=False,
                        scale=sum_dat / sum_bkg,
                    )

                    # histos_dat = [get_histo(inp_root, hname, s) for s in samples_dat]
                    # histos_bkg = [get_histo(inp_root, hname, s) for s in samples_bkg]

                    plotter.stackplot(
                        output_path / f"plot01_{hname}_log_2.png",
                        histos_dat,
                        histos_bkg,
                        [],
                        logy=True,
                        scale=sum_dat / sum_bkg,
                    )
                    # histos_dat = [get_histo(inp_root, hname, s) for s in samples_dat]
                    # histos_bkg = [get_histo(inp_root, hname, s) for s in samples_bkg]

                    # sum_dat = sum(h[0].GetBinContent(6) for h in histos_dat)
                    # sum_bkg = sum(h[0].GetBinContent(6) for h in histos_bkg)

                    # plotter.stackplot(
                    #     output_path / f"plot01_{hname}_lin_3.png",
                    #     histos_dat,
                    #     histos_bkg,
                    #     [],
                    #     logy=False,
                    #     scale=sum_dat / sum_bkg,
                    # )

                    # # histos_dat = [get_histo(inp_root, hname, s) for s in samples_dat]
                    # # histos_bkg = [get_histo(inp_root, hname, s) for s in samples_bkg]

                    # plotter.stackplot(
                    #     output_path / f"plot01_{hname}_log_3.png",
                    #     histos_dat,
                    #     histos_bkg,
                    #     [],
                    #     logy=True,
                    #     scale=sum_dat / sum_bkg,
                    # )

                    if df == "muon":
                        muon_dat = histos_dat[0][0].Clone("muon_dat")
                        for h in histos_bkg:
                            if h[0].GetName() == "DYJets":
                                muon_bkg = h[0].Clone("muon_bkg")
                            else:
                                muon_dat.Add(h[0], -1.0)
                    else:
                        elec_dat = histos_dat[0][0].Clone("elec_dat")
                        for h in histos_bkg:
                            if h[0].GetName() == "DYJets":
                                elec_bkg = h[0].Clone("elec_bkg")
                            else:
                                elec_dat.Add(h[0], -1.0)

                muon_scale = muon_dat.GetBinContent(1) / muon_bkg.GetBinContent(1)
                muon_ratio = muon_dat.Clone("muon_ratio")
                muon_ratio.Divide(muon_dat, muon_bkg, 1.0, muon_scale)

                elec_scale = elec_dat.GetBinContent(1) / elec_bkg.GetBinContent(1)
                elec_ratio = elec_dat.Clone("elec_ratio")
                elec_ratio.Divide(elec_dat, elec_bkg, 1.0, elec_scale)

                both_ratio = muon_dat.Clone("both_ratio")
                both_ratio.Add(muon_ratio, elec_ratio, 0.5, 0.5)
                c1 = ROOT.TCanvas("c1")

                c1.SetRightMargin(0.09)
                c1.SetLeftMargin(0.14)
                c1.SetBottomMargin(0.14)
                old_ratio = muon_ratio.Clone("old_ratio")
                old_ratio.Reset()
                for i, x in enumerate(ISR_CORRECTIONS):
                    x = x / 1.150
                    old_ratio.SetBinContent(i + 1, x)
                    old_ratio.SetBinError(i + 1, abs(x - 1.0))
                old_ratio.SetMinimum(0.3)
                old_ratio.SetMaximum(1.2)
                old_ratio.SetStats(0)
                old_ratio.SetTitle(
                    "ISR Correction for Drell Yan; p_{T} [GeV/c]; Data / MC"
                )
                old_ratio1 = muon_ratio.Clone("old_ratio")
                old_ratio1.Reset()
                for i, x in enumerate(ISR_CORRECTIONS):
                    x = x / 1.150
                    old_ratio1.SetBinContent(i + 1, x)
                    old_ratio1.SetBinError(i + 1, 0.5 * abs(x - 1.0))
                old_ratio1.SetStats(0)
                both_ratio.SetMarkerSize(1.5)
                muon_ratio.SetMarkerSize(1.5)
                elec_ratio.SetMarkerSize(1.5)
                old_ratio.SetMarkerSize(1.5)
                old_ratio1.SetMarkerSize(1.5)
                both_ratio.SetMarkerStyle(20)
                muon_ratio.SetMarkerStyle(21)
                elec_ratio.SetMarkerStyle(22)
                old_ratio.SetMarkerStyle(23)
                old_ratio1.SetMarkerStyle(23)
                both_ratio.SetMarkerColor(ROOT.kRed)
                both_ratio.SetLineColor(ROOT.kRed)
                muon_ratio.SetMarkerColor(ROOT.kGreen)
                muon_ratio.SetLineColor(ROOT.kGreen)
                elec_ratio.SetMarkerColor(ROOT.kBlue)
                elec_ratio.SetLineColor(ROOT.kBlue)
                old_ratio.SetMarkerColor(6)
                old_ratio1.SetMarkerColor(6)
                old_ratio.SetLineColor(6)
                old_ratio.SetFillColor(ROOT.kGray)
                old_ratio.SetFillStyle(3644)
                old_ratio1.SetFillColor(ROOT.kGray)
                old_ratio1.SetLineColor(6)
                old_ratio1.SetFillStyle(3344)
                old_ratio.Draw("e3")
                old_ratio.GetXaxis().SetTitleOffset(1)
                old_ratio.GetYaxis().SetTitleOffset(2)
                old_ratio.Draw("e3")
                old_ratio1.Draw("e3 same")
                # old_ratio1.SetFillStyle(0)
                # old_ratio1.Draw("lp hist same")
                # old_ratio1.SetFillStyle(3344)
                muon_ratio.Draw("l hist same")
                muon_ratio.Draw("p same")
                elec_ratio.Draw("l hist same")
                elec_ratio.Draw("p same")
                both_ratio.Draw("l hist same")
                both_ratio.Draw("p same")

                l = ROOT.TLegend(0.75, 0.7, 0.9, 0.89)
                l.SetBorderSize(0)
                l.AddEntry(old_ratio, "Official", "p")
                l.AddEntry(old_ratio, "100% Error", "f")
                l.AddEntry(old_ratio1, "50% Error", "f")
                l.AddEntry(muon_ratio, "#mu", "p")
                l.AddEntry(elec_ratio, "e", "p")
                l.AddEntry(both_ratio, "avg.", "p")
                l.Draw()

                c1.cd()
                t1 = ROOT.TText(0.01, 0.97, "CMS Preliminary")
                t1.SetNDC()
                t1.SetTextFont(40)
                t1.SetTextSize(0.03)
                t1.Draw()

                t2 = ROOT.TLatex()
                t2.SetNDC()
                # t2.SetTextFont(41)
                t2.SetTextSize(0.03)
                t2.SetTextAlign(30)
                t2.DrawLatex(0.9, 0.97, f"{p} ({int_lumi[p]} fb^{{-1}})")
                # t2.Draw()

                c1.SaveAs(str(output_path / "plot01.png"))

                out_root.Close()


if __name__ == "__main__":
    main()
