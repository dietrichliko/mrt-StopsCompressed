#!/usr/bin/env python

from typing import Tuple

import ROOT


MUON_MAPS = [
    "mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10.root:mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10_merged",
    "2016_mu_sf.root:muon_SF_IpIsoSpec_2D_merged",
]

def read_hist(histo_path: str) -> Tuple[list[float], list[float], list[float]]:

    fpath, hname = histo_path.split(":")
    

    f = ROOT.TFile(fpath)
    h = f.Get(hname)
    assert h.__class__.__name__ == "TH2F"    
    ax = h.GetXaxis()
    nx = ax.GetNbins()
    ex = [ax.GetBinLowEdge(i+1) for i in range(nx)]
    ex.append(ax.GetBinUpEdge(nx))
    ay = h.GetYaxis()
    ny = ay.GetNbins()
    ey = [ay.GetBinLowEdge(i+1) for i in range(nx)]
    ey.append(ay.GetBinUpEdge(nx))
    data = []
    for ix in range(nx):
        for iy in range(ny):
            data.append(h.GetBinContent(ix+1,iy+1))
    return ex, ey, data

def make_correction(dir: str, eff_maps: list[str]):

    ex, ey, data = read_hist(f"{dir}/{eff_maps[0]}")
    for eff_map in eff_maps[1:]:
        ex1, ey1, data1 = read_hist(f"{dir}/{eff_map}")
        assert ex == ex1
        assert ey == ey1
        data = [x*y for x, y in zip(data, data1)]

    print(ex)
    print(ey)
    print(data)

if __name__ == "__main__":

    make_correction("data/LeptonSF", MUON_MAPS)    
