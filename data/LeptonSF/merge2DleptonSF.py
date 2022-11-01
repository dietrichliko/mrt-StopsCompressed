import ROOT
from array import array

ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetPaintTextFormat("1.4f")

def weightedAverage(v1,e1,v2,e2) :

    w1 = 1./e1**2
    w2 = 1./e2**2

    w1_new = w1/(w1+w2)
    w2_new = w2/(w1+w2)
    v = (v1*w1_new+v2*w2_new)
    e = ((e1*w1_new)**2 + (e2*w2_new)**2)**0.5 
    return v, e

######### ELECTRONS 
#for name, name2 in [("2016_el_sf","ele_SF_IpIso_2D"),("el_SF_2D_VetoWP_cent_VetoWP_priv_5-10_2016","el_SF_2D_VetoWP_cent_VetoWP_priv_5-10_2016")] :
for name, name2 in [("2017_el_sf","ele_SF_IpIso_2D"),("el_SF_2D_VetoWP_cent_VetoWP_priv_5-10_2017","el_SF_2D_VetoWP_cent_VetoWP_priv_5-10_2017")] :
#for name, name2 in [("2017_el_sf","ele_SF_IpIso_2D"),("el_SF_2D_VetoWP_cent_VetoWP_priv_5-10_2018","el_SF_2D_VetoWP_cent_VetoWP_priv_5-10_2018")] :
    
    _file = ROOT.TFile("{}.root".format(name))
    TH2F = _file.Get("{}".format(name2))
    TH2F_merged = TH2F.Clone("{}_merged".format(name2))
         
    test = ROOT.TFile("{}_merged.root".format(name),"recreate")

    c1 = ROOT.TCanvas("c1")
    c1.SetLogy()
    TH2F.GetZaxis().SetRangeUser(0.6,1.2)
    ROOT.gStyle.SetPaintTextFormat("1.4f")

    TH2F.Draw("colz text89 e")
    c1.SaveAs("{}.png".format(name2))
    c1.Write()

    c2 = ROOT.TCanvas("c2")
    c2.SetLogy()
    ROOT.gStyle.SetPaintTextFormat("1.4f")
    ROOT.gStyle.SetOptStat(0)
    TH2F_merged.GetZaxis().SetRangeUser(0.6,1.2)

    TH2F_merged.Draw("colz text89 e")
    c2.SaveAs("{}_merged.png".format(name2))
    c2.Write()


    TH2F_merged.Write()


    _file.Close
    test.Close()

############ MUONS ######################
#for name, name2 in [("mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10","mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-10"), ("2016_mu_sf","muon_SF_IpIsoSpec_2D")] :
for name, name2 in [("mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-20","mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-20"), ("2017_mu_sf","muon_SF_IpIsoSpec_2D")] :
#for name, name2 in [("mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-20_2018","mu_SF_2D_LooseWP_cent_LooseWP_priv_3p5-20_2018"), ("2018_mu_sf","muon_SF_IpIsoSpec_2D")] :


    _file = ROOT.TFile("{}.root".format(name))
    TH2F = _file.Get("{}".format(name2))

    TH2F_merged = TH2F.Clone("{}_merged".format(name2))


    # combine bins in x-range
    low_pt_merge = []
    for j in range(TH2F.GetNbinsY()) :
        c1 = TH2F.GetBinContent(1,j+1)
        e1 = TH2F.GetBinError(1,j+1)

        c2 = TH2F.GetBinContent(2,j+1)
        e2 = TH2F.GetBinError(2,j+1)

        low_pt_merge.append(weightedAverage(c1,e1,c2,e2))
        

    for eta_i in range(2) :
        v,e = weightedAverage(low_pt_merge[2*eta_i][0],low_pt_merge[2*eta_i][1],low_pt_merge[2*eta_i+1][0],low_pt_merge[2*eta_i+1][1])
    
        TH2F_merged.SetBinContent(1,2*eta_i+1,v)
        TH2F_merged.SetBinContent(2,2*eta_i+1,v)
        TH2F_merged.SetBinContent(1,2*eta_i+2,v)
        TH2F_merged.SetBinContent(2,2*eta_i+2,v)
        
        TH2F_merged.SetBinError(1,2*eta_i+1,e)
        TH2F_merged.SetBinError(2,2*eta_i+1,e)
        TH2F_merged.SetBinError(1,2*eta_i+2,e)
        TH2F_merged.SetBinError(2,2*eta_i+2,e)
        


    test = ROOT.TFile("{}_merged.root".format(name),"recreate")

    c1 = ROOT.TCanvas("c1")
    c1.SetLogx()
    TH2F.GetZaxis().SetRangeUser(0.95,1.05)
    ROOT.gStyle.SetPaintTextFormat("1.4f")

    TH2F.Draw("colz text89 e")
    c1.SaveAs("{}.png".format(name2))
    c1.Write()

    c2 = ROOT.TCanvas("c2")
    c2.SetLogx()
    ROOT.gStyle.SetPaintTextFormat("1.4f")
    ROOT.gStyle.SetOptStat(0)
    # TH2F_new.GetZaxis().SetRangeUser(0.95,1.05)
    TH2F_merged.GetZaxis().SetRangeUser(0.95,1.05)

    # TH2F_new.Draw("colz text89 e")
    TH2F_merged.Draw("colz text89 e")
    c2.SaveAs("{}_merged.png".format(name2))
    c2.Write()


    # TH2F_new.Write()
    TH2F_merged.Write()


    _file.Close
    test.Close()
