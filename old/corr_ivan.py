#!/usr/bin/env python
from array import array

import ROOT

edge = [0, 50, 100, 150, 200, 300, 400, 600, 1000]

c = 0.94
val = [0, 1, 1.052, 1.179, 1.150, 1.057, 1.000, 0.912, 0.783]
for i in range(8):
    val[i] = c * val[i]
err = [0, 0, 0.001, 0.002, 0.003, 0.004, 0.008, 0.012, 0.023]

h = ROOT.TH1F("ivan", "Correction Factor", len(edge)-1, array("f", edge))
h.SetStats(0)
h.SetContent(array("d", val))
h.SetError(array("d", err))

c = ROOT.TCanvas()
h.SetMarkerStyle(20)
h.SetMarkerSize(1)
h.SetMinimum(0.5)
h.SetMaximum(1.5)
h.Draw("pe")

l = ROOT.TLine(h.GetXaxis().GetXmin(), 1.0, h.GetXaxis().GetXmax(), 1.0)
l.Draw()
c.SetLogy()
c.SaveAs("ivan.png")
