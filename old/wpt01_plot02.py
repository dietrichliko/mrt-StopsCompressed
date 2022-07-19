#!/usr/bin/env python
import json
import pathlib
from mrtools import plotter
from typing import Any

import ROOT


PERIODES = ("Run2016preVFP", "Run2016postVFP", "Run2017", "Run2018")

BKG_SAMPLES = ("WJets", "TT", "T", "TTX", "DY", "DYINV", "QCD")

INPUT_PATH = pathlib.Path("/scratch-cbe/users/dietrich.liko/WPT")
INPUT_NAME = "wpt01_{period}"

MAXIMUM = 3.0


def main():
    """Plots for WPT."""
    plotter.tdr_style()

    stat: dict[str, Any] = {}
    for p in PERIODES:
        inp_json = (INPUT_PATH / INPUT_NAME.format(period=p)).with_suffix(".json")
        with open(inp_json, "r") as inp:
            stat[p] = json.load(inp)

    mu_nr_events = []
    el_nr_events = []
    mu_sum_weights = []
    el_sum_weights = []
    mu_ratio = []
    el_ratio = []
    for p in PERIODES:
        mu_nr_events.append(stat[p]["SingleMuon"]["df_mu3_nr_events"])
        el_nr_events.append(stat[p]["SingleElectron"]["df_el3_nr_events"])
        mu_sum_weights.append(
            sum(stat[p][s]["df_mu3_sum_weights"] for s in BKG_SAMPLES)
        )
        el_sum_weights.append(
            sum(stat[p][s]["df_el3_sum_weights"] for s in BKG_SAMPLES)
        )
        mu_ratio.append(mu_nr_events[-1] / mu_sum_weights[-1])
        el_ratio.append(el_nr_events[-1] / el_sum_weights[-1])

    c1 = ROOT.TCanvas()
    c1.SetLogy()

    h_mu = ROOT.TH1F("mu", "Muons", 4, 0.5, 4.5)
    h_mu.SetCanExtend(ROOT.TH1.kAllAxes)
    for label, value in zip(PERIODES, mu_ratio):
        h_mu.Fill(label, value)
    h_mu.LabelsDeflate()
    # h_mu.SetMinimum(math.exp(-math.log(MAXIMUM)))
    h_mu.SetMinimum(1 / MAXIMUM)
    h_mu.SetMaximum(MAXIMUM)
    h_mu.SetMarkerSize(1.5)
    h_mu.SetMarkerStyle(20)
    h_mu.SetMarkerColor(ROOT.kRed)

    h_el = ROOT.TH1F("el", "Electrons", 4, 0.5, 4.5)
    h_el.SetCanExtend(ROOT.TH1.kAllAxes)
    for label, value in zip(PERIODES, el_ratio):
        h_el.Fill(label, value)
    h_el.LabelsDeflate()
    # h_el.SetMinimum(math.exp(-math.log(MAXIMUM)))
    h_el.SetMinimum(1.0 / MAXIMUM)
    h_el.SetMaximum(MAXIMUM)
    h_el.SetMarkerSize(1.5)
    h_el.SetMarkerStyle(22)
    h_el.SetMarkerColor(ROOT.kBlue)
    h_el.GetYaxis().SetNdivisions(20)

    h_mu.Draw("hist p")
    h_el.Draw("hist p same")

    legend = ROOT.TLegend(0.7, 0.8, 0.95, 0.95)
    legend.AddEntry(h_mu, "Muons", "p")
    legend.AddEntry(h_el, "Electrons", "p")
    legend.SetFillStyle(0)
    legend.SetShadowColor(ROOT.kWhite)
    legend.SetBorderSize(0)
    legend.Draw()

    line = []
    for y in (0.5, 1, 2):
        line.append(
            ROOT.TLine(h_mu.GetXaxis().GetXmin(), y, h_mu.GetXaxis().GetXmax(), y)
        )
        line[-1].Draw()

    c1.SaveAs(str(INPUT_PATH / "plot01.png"))

    mu_values = {}
    el_values = {}
    for p in PERIODES:
        mu_sum = sum(stat[p][s]["df_mu3_sum_weights"] for s in BKG_SAMPLES)
        el_sum = sum(stat[p][s]["df_el3_sum_weights"] for s in BKG_SAMPLES)
        mu_values[p] = {
            s: 100 * stat[p][s]["df_mu3_sum_weights"] / mu_sum for s in BKG_SAMPLES
        }
        el_values[p] = {
            s: 100 * stat[p][s]["df_el3_sum_weights"] / el_sum for s in BKG_SAMPLES
        }

    for p in PERIODES:
        print(f"{p:<20} :", end="")
        for s in BKG_SAMPLES:
            print(f"{mu_values[p][s]:6.3f}", end="")
        print()

    for p in PERIODES:
        print(f"{p:<20} :", end="")
        for s in BKG_SAMPLES:
            print(f"{el_values[p][s]:6.3f}", end="")
        print()

    h_mu = ROOT.TH2F("h_mu", "Muons", 7, -0.5, 6.5, 4, -0.5, 3.5)
    h_el = ROOT.TH2F("h_el", "Electrons", 7, -0.5, 6.5, 4, -0.5, 3.5)
    h_mu.SetCanExtend(ROOT.TH1.kAllAxes)
    h_mu.SetStats(0)
    h_el.SetCanExtend(ROOT.TH1.kAllAxes)
    h_el.SetStats(0)

    for p in PERIODES:
        for s in BKG_SAMPLES:
            h_mu.Fill(s, p, mu_values[p][s])
            h_el.Fill(s, p, el_values[p][s])

    h_mu.LabelsDeflate("X")
    h_mu.LabelsDeflate("Y")
    h_mu.LabelsOption("v")

    h_el.LabelsDeflate("X")
    h_el.LabelsDeflate("Y")
    h_el.LabelsOption("v")

    h_mu.GetXaxis().SetLabelSize(0.1)
    h_mu.GetYaxis().SetLabelSize(0.1)
    h_el.GetXaxis().SetLabelSize(0.1)
    h_el.GetYaxis().SetLabelSize(0.1)

    c2 = ROOT.TCanvas()
    c2.Divide(1, 2, 0, 0)

    ROOT.gStyle.SetPaintTextFormat("5.1f")
    h_mu.SetMarkerSize(4.0)
    h_el.SetMarkerSize(4.0)

    p1 = c2.cd(1)
    p1.SetGrid()
    p1.SetLeftMargin(0.3)
    p1.SetBottomMargin(0.3)

    h_mu.GetXaxis().SetTitleOffset(3)

    h_mu.Draw("TEXT")

    p2 = c2.cd(2)
    p2.SetGrid()
    p2.SetLeftMargin(0.3)
    p2.SetBottomMargin(0.3)
    h_el.Draw("TEXT")

    c2.SaveAs(str(INPUT_PATH / "plot02.png"))


if __name__ == "__main__":
    main()
