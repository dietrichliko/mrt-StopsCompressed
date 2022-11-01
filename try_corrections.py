#!/usr/bin/env python

from typing import Tuple

# from correctionlib import convert

from fix import convert

MUON_MAPS = [
    "mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10.root:mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10_merged",
    "2016_mu_sf.root:muon_SF_IpIsoSpec_2D_merged",
]

if __name__ == "__main__":

    dir = "data/LeptonSF"

    corr1 = convert.from_uproot_THx(
        "data/LeptonSF/mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10.root:mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10_merged"
    )
    print(corr1)

    # print("data/LeptonSF/mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10.root:mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10_merged")
    # print(f"{dir}/{MUON_MAPS[0]}")
    # corr1 = convert.from_uproot_THx(f"{dir}/{MUON_MAPS[0]}")
    # corr2 = convert.from_uproot_THx(f"{dir}/{MUON_MAPS[1]}")
