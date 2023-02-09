#!/usr/bin/env python
# Find DY gen info
import logging
import os
import pathlib
from mrtools import utils
from typing import Any

import click
import ROOT

logging.basicConfig(
    format="%(asctime)s - %(levelname)s -  %(name)s - %(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.WARNING,
)
log = logging.getLogger("mrtools")

ROOT.PyConfig.IgnoreCommandLineOptions = True

PATH = pathlib.Path("/scratch-cbe/users/dietrich.liko/StopsCompressed/nanoTuples")

TAG = {
    "Run2016preVFP": "compstops_UL16APVv9_nano_v8",
    "Run2016postVFP": "compstops_UL16v9_nano_v8",
    "Run2017": "compstops_UL17v9_nano_v8",
    "Run2018": "compstops_UL17v9_nano_v8",
}

HT_BINS = [
    "70to100",
    "100to200",
    "200to400",
    "400to600",
    "600to800",
    "800to1200",
    "1200to2500",
    "2500toInf",
]


def make_post_chains(period: str, ht_bins: bool) -> dict[str, Any]:
    """Create ROOT Chains for the various datasets."""
    if ht_bins:
        datasets = [f"DYJetsToLL_M50_HT{ht}" for ht in HT_BINS]
    else:
        datasets = ["DYJetsToLL_M50_LO", "DYJetsToLL_M50_LO_ext"]

    datasets.append("DYJetsToLL_M10to50_LO")

    chains: dict[str, Any] = {}
    for dataset in os.listdir(PATH / TAG[period] / "DoubleLep"):
        # if (
        #     dataset.startswith("DYJetsToLL_M50_HT")
        #     or dataset == "DYJetsToLL_M10to50_LO"
        # ):
        if dataset in datasets:
            chains[dataset] = ROOT.TChain("Events")
            cnt = 0
            for name in os.listdir(PATH / TAG[period] / "DoubleLep" / dataset):
                path = PATH / TAG[period] / "DoubleLep" / dataset / name
                print(path)
                chains[dataset].Add(str(path))
                cnt += 1
            log.debug("Dataset %s with %d files", dataset, cnt)

    return chains


def draw_header(canvas: Any, sample: str, period: str) -> Any:

    canvas.cd()

    t1 = ROOT.TText(0.01, 0.97, "CMS Preliminary")
    t1.SetNDC()
    t1.SetTextFont(40)
    t1.SetTextSize(0.03)
    t1.Draw()

    t2 = ROOT.TText(0.9, 0.97, period)
    t2.SetNDC()
    t2.SetTextFont(40)
    t2.SetTextSize(0.03)
    t2.Draw()

    t3 = ROOT.TLatex()
    t3.SetNDC()
    # t3.SetTextFont(40)
    t3.SetTextSize(0.03)
    t3.DrawLatex(0.4, 0.97, sample)

    return t1, t2, t3


@click.command(context_settings=dict(max_content_width=120))
@click.option(
    "-p",
    "--period",
    default="Run2016preVFP",
    type=click.Choice(list(TAG.keys()), case_sensitive=False),
    help="Datataking period",
    show_default=True,
)
@click.option("--ht-bins/--no-ht-bins", default=False)
@click.option("--small/--no-small", default=False)
@click.option(
    "-o",
    "--output",
    default="dygen.root",
    type=click.Path(dir_okay=False, writable=True, path_type=pathlib.Path),
    help="Output file",
    show_default=True,
)
@utils.click_option_logging(log)
def main(period: str, small: bool, ht_bins: bool, output: pathlib.Path):
    """Drell Yan Generator Info."""
    log.info("Analysis of Drell Yan Generator info")
    ROOT.gROOT.SetBatch()
    ROOT.gErrorIgnoreLevel = ROOT.kError
    if not small:
        ROOT.EnableImplicitMT()
    ROOT.gInterpreter.Declare('#include "dygen_inc.h"')

    log.info("Period %s", period)
    chains = make_post_chains(period, ht_bins)

    df: dict[str, Any] = {}
    histos: dict[str, Any] = {}
    events: dict[str, Any] = {}
    for dataset, chain in chains.items():
        df[dataset] = ROOT.RDataFrame(chain)
        if small:
            df[dataset] = df[dataset].Range(0, 10)

        df[dataset] = df[dataset].Define(
            "genDY_pt",
            "GenDY_pt(GenPart_pt, GenPart_eta, GenPart_phi, GenPart_mass, GenPart_pdgId, GenPart_status, GenPart_statusFlags)",
        )

        df[dataset] = df[dataset].Define(
            "genDY_mass",
            "GenDY_mass(GenPart_pt, GenPart_eta, GenPart_phi, GenPart_mass, GenPart_pdgId, GenPart_status, GenPart_statusFlags)",
        )

        histos[f"{dataset}_pt"] = (
            df[dataset]
            .Filter("abs(genDY_mass-91.2)<10. && genDY_pt > 0.")
            .Histo1D((f"{dataset}_pt", "p_{T}", 100, -2.0, 500.0), "genDY_pt", "weight")
        )
        histos[f"{dataset}_mass"] = df[dataset].Histo1D(
            (f"{dataset}_mass", "Mass", 100, -2.0, 200.0), "genDY_mass", "weight"
        )
        histos[f"{dataset}_nJet"] = df[dataset].Histo1D(
            (f"{dataset}_nJet", "nJet", 21, -0.5, 20.5), "nJet", "weight"
        )
        histos[f"{dataset}_HT"] = df[dataset].Histo1D(
            (f"{dataset}_HT", "HT", 100, 0, 500.0), "HT", "weight"
        )
        df[dataset] = df[dataset].Filter("HT>100")
        histos[f"{dataset}_pt1"] = (
            df[dataset]
            .Filter("abs(genDY_mass-91.2)<10. && genDY_pt > 0.")
            .Histo1D(
                (f"{dataset}_pt1", "p_{T}", 100, -2.0, 500.0), "genDY_pt", "weight"
            )
        )
        histos[f"{dataset}_mass1"] = df[dataset].Histo1D(
            (f"{dataset}_mass1", "Mass", 100, -2.0, 200.0), "genDY_mass", "weight"
        )
        events[dataset] = df[dataset].Count()

    ROOT.RDF.RunGraphs(list(histos.values()) + list(events.values()))

    for dataset, evt in events.items():
        print(f"Number of events for dataset {dataset} is {evt.GetValue()}")

    histos = {key: h.GetValue() for key, h in histos.items()}

    histos["DYJetsToLL_pt"] = histos["DYJetsToLL_M10to50_LO_pt"].Clone("DYJetsToLL_pt")
    histos["DYJetsToLL_mass"] = histos["DYJetsToLL_M10to50_LO_mass"].Clone(
        "DYJetsToLL_mass"
    )
    histos["DYJetsToLL_pt1"] = histos["DYJetsToLL_M10to50_LO_pt1"].Clone(
        "DYJetsToLL_pt1"
    )
    histos["DYJetsToLL_mass1"] = histos["DYJetsToLL_M10to50_LO_mass1"].Clone(
        "DYJetsToLL_mass1"
    )

    if ht_bins:
        for ht in HT_BINS[1:]:
            histos["DYJetsToLL_pt"] = (
                histos["DYJetsToLL_pt"] + histos[f"DYJetsToLL_M50_HT{ht}_pt"]
            )
            histos["DYJetsToLL_mass"] = (
                histos["DYJetsToLL_mass"] + histos[f"DYJetsToLL_M50_HT{ht}_mass"]
            )
            histos["DYJetsToLL_pt1"] = (
                histos["DYJetsToLL_pt1"] + histos[f"DYJetsToLL_M50_HT{ht}_pt1"]
            )
            histos["DYJetsToLL_mass1"] = (
                histos["DYJetsToLL_mass1"] + histos[f"DYJetsToLL_M50_HT{ht}_mass1"]
            )
            sample = "Z^{*} / #gamma #rightarrow Jets + l^{+}l^{-} (HT Bins)"
    else:
        histos["DYJetsToLL_pt"] = (
            histos["DYJetsToLL_pt"] + histos["DYJetsToLL_M50_LO_pt"]
        )
        histos["DYJetsToLL_mass"] = (
            histos["DYJetsToLL_mass"] + histos["DYJetsToLL_M50_LO_mass"]
        )
        histos["DYJetsToLL_pt1"] = (
            histos["DYJetsToLL_pt1"] + histos["DYJetsToLL_M50_LO_pt1"]
        )
        histos["DYJetsToLL_mass1"] = (
            histos["DYJetsToLL_mass1"] + histos["DYJetsToLL_M50_LO_mass1"]
        )
        sample = "Z^{*} / #gamma #rightarrow Jets + l^{+}l^{-} (No HT Bins)"

    out = ROOT.TFile(str(output), "RECREATE")
    for h in histos.values():
        h.Write()
    out.Close()

    c1 = ROOT.TCanvas("c1", "", 800, 600)

    c1.Divide(2, 2, 0.01, 0.01)
    ROOT.gStyle.SetOptStat(0)

    histos["DYJetsToLL_mass"].SetTitle(
        "Dilepton Mass;Mass [GeV/c^{2}];Weighted entries"
    )
    histos["DYJetsToLL_mass1"].SetFillColor(ROOT.kBlue)
    histos["DYJetsToLL_mass1"].SetFillStyle(3944)

    c1.cd(1)
    histos["DYJetsToLL_mass"].Draw("hist")
    histos["DYJetsToLL_mass1"].Draw("same hist")
    p12 = c1.cd(2)
    p12.SetLogy()
    histos["DYJetsToLL_mass"].Draw("hist")
    histos["DYJetsToLL_mass1"].Draw("same hist")

    histos["DYJetsToLL_pt"].SetTitle(
        "Dilepton p_{T} for |m_{ll}-M_{Z}| < 10;p_{T} [GeV/c];Weighted entries"
    )
    histos["DYJetsToLL_pt1"].SetFillColor(ROOT.kBlue)
    histos["DYJetsToLL_pt1"].SetFillStyle(3944)

    c1.cd(3)
    histos["DYJetsToLL_pt"].Draw("hist")
    histos["DYJetsToLL_pt1"].Draw("samehist")
    p14 = c1.cd(4)
    p14.SetLogy()
    histos["DYJetsToLL_pt"].Draw("hist")
    histos["DYJetsToLL_pt1"].Draw("samehist")

    t = draw_header(c1, sample, period)
    c1.SaveAs(str(output.with_name(f"{output.stem}_ptmass.png")))

    c2 = ROOT.TCanvas("c2", "", 800, 400)
    c2.Divide(2, 1, 0.01, 0.01)
    if ht_bins:
        hs = ROOT.THStack("hs", ";HT [GeV/c^{2}];Weighted entries")
        l = ROOT.TLegend(0.6, 0.63, 0.9, 0.88)
        l.SetBorderSize(0)
        for i, ht in enumerate(HT_BINS):
            h = histos[f"DYJetsToLL_M50_HT{ht}_HT"]
            h.SetFillColor(i + 2)
            hs.Add(h)
            l.AddEntry(h, ht, "f")

        p1 = c2.cd(1)
        p1.SetLeftMargin(0.2)
        hs.Draw("hist")
        l.Draw()
        p2 = c2.cd(2)
        p2.SetLeftMargin(0.2)
        p2.SetLogy()
        hs.Draw("hist")
        l.Draw()
    else:
        if "DYJetsToLL_M50_LO_ext_HT" in histos:
            h1 = histos["DYJetsToLL_M50_LO_HT"] + histos["DYJetsToLL_M50_LO_ext_HT"]
        else:
            h1 = histos["DYJetsToLL_M50_LO_HT"]
        h1.SetFillColor(ROOT.kBlue)
        c2.cd(1)
        h1.Draw("hist")
        p2 = c2.cd(2)
        p2.SetLogy()
        h1.Draw("hist")

    t = draw_header(c2, sample, period)

    c2.SaveAs(str(output.with_name(f"{output.stem}_ht.png")))


if __name__ == "__main__":
    main()
