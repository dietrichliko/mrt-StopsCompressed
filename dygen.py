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


def make_post_chains(period: str) -> dict[str, Any]:

    chains: dict[str, Any] = {}
    for dataset in os.listdir(PATH / TAG[period] / "DoubleLep"):
        if dataset.startswith("DYJetsToLL_M50_HT"):
            chains[dataset] = ROOT.TChain("Events")
            cnt = 0
            for name in os.listdir(PATH / TAG[period] / "DoubleLep" / dataset):
                path = PATH / TAG[period] / "DoubleLep" / dataset / name
                chains[dataset].Add(str(path))
                cnt += 1
            log.debug("Dataset %s with %d files", dataset, cnt)

    return chains


@click.command(context_settings=dict(max_content_width=120))
@click.option(
    "-p",
    "--period",
    default="Run2016preVFP",
    type=click.Choice(list(TAG.keys()), case_sensitive=False),
    help="Datataking period",
    show_default=True,
)
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
def main(period: str, small: bool, output: pathlib.Path):
    """Drell Yan Generator Info."""
    log.info("Analysis of Drell Yan Generator info")
    ROOT.gROOT.SetBatch()
    ROOT.gErrorIgnoreLevel = ROOT.kError
    if not small:
        ROOT.EnableImplicitMT()
    ROOT.gInterpreter.Declare('#include "dygen_inc.h"')

    chain = ROOT.TChain("Events")

    log.info("Period %s", period)
    chains = make_post_chains(period)

    df: dict[str, Any] = {}
    histos: dict[str, Any] = {}
    events: dict[str, Any] = {}
    for dataset, chain in chains.items():
        df[dataset] = ROOT.RDataFrame(chain)
        if small:
            df[dataset] = df[dataset].Range(0, 10)

        df[dataset] = df[dataset].Define(
            "genDY_pt",
            "GenDY_pt(GenPart_pt, GenPart_phi, GenPart_pdgId, GenPart_status, GenPart_statusFlags)",
        )

        histos[f"{dataset}_pt"] = df[dataset].Histo1D(
            (f"{dataset}_pt", "p_{T}", 100, 0.0, 1000.0), "genDY_pt", "weight"
        )
        events[dataset] = df[dataset].Count()

    ROOT.RDF.RunGraphs(list(histos.values()) + list(events.values()))

    for dataset, evt in events.items():
        print(f"Number of events for dataset {dataset} is {evt.GetValue()}")

    histos1 = {key: h.GetValue() for key, h in histos.items()}

    histos1["DYJetsToLL_M50_HTall_pt"] = histos1["DYJetsToLL_M50_HT70to100_pt"].Clone(
        "DYJetsToLL_M50_HTall_pt"
    )

    for ht in HT_BINS[1:]:
        histos1["DYJetsToLL_M50_HTall_pt"] = (
            histos1["DYJetsToLL_M50_HTall_pt"] + histos1[f"DYJetsToLL_M50_HT{ht}_pt"]
        )

    out = ROOT.TFile(str(output), "RECREATE")
    for h in histos1.values():
        h.Write()
    out.Close()

    c1 = ROOT.TCanvas("c", "", 800, 800)
    c1.Divide(3, 3, 0.01, 0.01)

    ht_bins = HT_BINS

    for i in range(len(HT_BINS)):
        p = c1.cd(i + 1)
        # p.SetLogy()
        # p.SetLogx()
        h = histos1[f"DYJetsToLL_M50_HT{ht_bins[i]}_pt"]
        h.SetTitle(f"DYJetsToLL_M50_HT{ht_bins[i]}")
        h.SetStats(False)
        h.Draw()

    c1.SaveAs("dygen01.png")

    c1 = ROOT.TCanvas("c", "", 800, 400)
    c1.Divide(2, 1, 0.01, 0.01)

    histos1["DYJetsToLL_M50_HTall_pt"].SetStats(False)
    histos1["DYJetsToLL_M50_HTall_pt"].SetTitle("Dilepton p_{T} in DYJetsToLL, M50, HT Binning")
    
    p1 = c1.cd(1)
    histos1["DYJetsToLL_M50_HTall_pt"].Draw()
    c1.Update()
    l1 = ROOT.TLine(70.0, p1.GetUymin(), 70.0, p1.GetUymax())
    l1.Draw()

    p2 = c1.cd(2)
    p2.SetLogy()
    histos1["DYJetsToLL_M50_HTall_pt"].Draw()
    c1.Update()
    l2 = ROOT.TLine(70.0, 10**p2.GetUymin(), 70.0, 10**p2.GetUymax())
    l2.Draw()

    c1.SaveAs("dygen02.png")


if __name__ == "__main__":
    main()
