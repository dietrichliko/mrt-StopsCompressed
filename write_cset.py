#!/usr/bin/env python

import gzip
from typing import Tuple

import correctionlib.schemav2 as cs
import ROOT

MUON_MAPS = [
    "mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10.root:mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10_merged",
    "2016_mu_sf.root:muon_SF_IpIsoSpec_2D_merged",
]


def make_corr(histo_path: str) -> cs.Correction:

    fpath, hname = histo_path.split(":")

    f = ROOT.TFile(fpath)
    h = f.Get(hname)
    assert h.__class__.__name__ == "TH2F"
    ax = h.GetXaxis()
    nx = ax.GetNbins()
    ex = [ax.GetBinLowEdge(i + 1) for i in range(nx)]
    ex.append(ax.GetBinUpEdge(nx))
    ay = h.GetYaxis()
    ny = ay.GetNbins()
    ey = [ay.GetBinLowEdge(i + 1) for i in range(ny)]
    ey.append(ay.GetBinUpEdge(nx))
    content = []
    for ix in range(nx):
        for iy in range(ny):
            content.append(h.GetBinContent(ix + 1, iy + 1))

    return cs.Correction(
        name=hname,
        version=1,
        inputs=[
            cs.Variable(name="pt", type="real", description="Muon transverse momentum"),
            cs.Variable(name="eta", type="real", description="Muon eta"),
        ],
        output=cs.Variable(
            name="weight", type="real", description="Multiplicative event weight"
        ),
        data=cs.MultiBinning(
            nodetype="multibinning",
            inputs=["pt", "eta"],
            edges=[ex, ey],
            content=content,
            flow="clamp",
        ),
    )

    return corr


if __name__ == "__main__":
    corrections = []
    for eff_map in MUON_MAPS:
        corrections.append(make_corr(f"data/LeptonSF/{eff_map}"))
    
    compound_correction = cs.CompoundCorrection(
        name="muon_corr",
        inputs=[
            cs.Variable(name="pt", type="real", description="Muon transverse momentum"),
            cs.Variable(name="eta", type="real", description="Muon eta"),
        ],
        output=cs.Variable(
            name="weight", type="real", description="Multiplicative event weight"
        ),
        inputs_update=[],
        input_op="*",
        output_op="*",
        stack=[c.name for c in corrections]
    )

    cset = cs.CorrectionSet(
        schema_version=2, 
        corrections=corrections,
        compound_corrections=[compound_correction]
    )

    with gzip.open("muon.json.gz", "wt") as fout:
        fout.write(cset.json(exclude_unset=True))
