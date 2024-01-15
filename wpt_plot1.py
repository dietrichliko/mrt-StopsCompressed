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

                int_lumi[p] = float(muon_sample.attrs["integrated_luminosity"])

                muon_name = "muon_W_pt_varX"
                muon_data = get_histo(inp_root, muon_name, muon_sample)[0]
                for other in (
                    get_histo(inp_root, muon_name, s)[0] for s in other_samples
                ):
                    muon_data.Add(other, -1.0)
                muon_wjet = get_histo(inp_root, muon_name, wjet_sample)[0]

                muon_scale = muon_data.GetBinContent(1) / muon_wjet.GetBinContent(1)
                print(muon_wjet)
                print(type(muon_wjet))
                muon_ratio = muon_data.Clone("muon_ratio")
                muon_ratio.Divide(muon_data, muon_wjet, 1.0, muon_scale)

                elec_name = "elec_W_pt_varX"
                elec_data = get_histo(inp_root, muon_name, muon_sample)[0]
                for other in (
                    get_histo(inp_root, elec_name, s)[0] for s in other_samples
                ):
                    elec_data.Add(other, -1.0)
                elec_wjet = get_histo(inp_root, muon_name, wjet_sample)[0]

                elec_scale = elec_data.GetBinContent(1) / elec_wjet.GetBinContent(1)
                elec_ratio = elec_data.Clone("elec_ratio")
                elec_ratio.Divide(elec_data, elec_wjet, 1.0, elec_scale)

                both_ratio = muon_ratio.Clone("both_ratio")
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
                    "ISR Correction for W+ jets; p_{T} [GeV/c]; Data / MC"
                )

                both_ratio.SetMarkerSize(1.5)
                muon_ratio.SetMarkerSize(1.5)
                elec_ratio.SetMarkerSize(1.5)
                old_ratio.SetMarkerSize(1.5)
                both_ratio.SetMarkerStyle(20)
                muon_ratio.SetMarkerStyle(21)
                elec_ratio.SetMarkerStyle(22)
                old_ratio.SetMarkerStyle(22)
                both_ratio.SetMarkerColor(ROOT.kRed)
                both_ratio.SetLineColor(ROOT.kRed)
                muon_ratio.SetMarkerColor(ROOT.kGreen)
                muon_ratio.SetLineColor(ROOT.kGreen)
                elec_ratio.SetMarkerColor(ROOT.kBlue)
                elec_ratio.SetLineColor(ROOT.kBlue)
                old_ratio.SetMarkerColor(6)
                old_ratio.SetLineColor(6)
                old_ratio1 = old_ratio.Clone("old_ratio1")
                old_ratio.SetFillColor(ROOT.kGray)
                old_ratio.SetFillStyle(3018)
                old_ratio.Draw("e3")
                old_ratio.GetXaxis().SetTitleOffset(1)
                old_ratio.GetYaxis().SetTitleOffset(2)
                old_ratio.Draw("e3")
                old_ratio1.Draw("hist l same")
                muon_ratio.Draw("l hist same")
                muon_ratio.Draw("p same")
                elec_ratio.Draw("l hist same")
                elec_ratio.Draw("p same")
                both_ratio.Draw("l hist same")
                both_ratio.Draw("p same")

                l1 = ROOT.TLegend(0.75, 0.7, 0.9, 0.89)
                l1.SetBorderSize(0)
                l1.AddEntry(old_ratio, "Offical", "p")
                l1.AddEntry(muon_ratio, "#mu", "p")
                l1.AddEntry(elec_ratio, "e", "p")
                l1.AddEntry(both_ratio, "avg.", "p")
                l1.Draw()

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

                inp_root.Close()


if __name__ == "__main__":
    main()
