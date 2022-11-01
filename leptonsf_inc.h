#ifndef LEPTONSF_INC_H
#define LEPTONSF_INC_H

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>

#include "correction.h"

// To import in PyROOT
//
// import ROOT
// ROOT.gROOT.ProcessLine(".include
// /groups/hephy/cms/dietrich.liko/conda/envs/mrt/lib/python3.10/site-packages/correctionlib/include")
// ROOT.gSystem.Load("/groups/hephy/cms/dietrich.liko/conda/envs/mrt/lib/python3.10/site-packages/correctionlib/lib/libcorrectionlib.so")
// ROOT.gROOT.processLine('#include "leptonsf_inc.h"')
class MuonSF {
 public:
  MuonSF(const std::string& period, const std::string& cset_file,
         const std::string& muon_id) {
    cset_ = correction::CorrectionSet::from_file(cset_file);
    std::string corr_name = "NUM_" + muon_id + "_DEN_genTracks";
    period_ = period.rfind("Run", 0) == 0 ? period.substr(3) : period;
    period_.append("_UL");
    bool found = false;
    for (auto it = cset_->begin(); it != cset_->end(); ++it) {
      found = found || it->first == corr_name;
    }
    if (!found) {
      throw std::invalid_argument("No correction for " + muon_id);
    }
    corr_ = cset_->at(corr_name);
  }

  double operator()(double pt, double eta) const {
    return corr_->evaluate({period_, std::abs(eta), pt, "sf"});
  }

 private:
  std::unique_ptr<correction::CorrectionSet> cset_;
  correction::Correction::Ref corr_;
  std::string period_;
};

class ElectronSF {
 public:
  ElectronSF(const std::string& period, const std::string& cset_file,
             const std::string& working_point) {
    cset_ = correction::CorrectionSet::from_file(cset_file);
    working_point_ = working_point;

    period_ = period.rfind("Run", 0) == 0 ? period.substr(3) : period;
  }
  double operator()(double pt, double eta) const {
    return cset_->at("UL-Electron-ID-SF")
        ->evaluate({period_, "sf", working_point_, eta, pt});
  }

 private:
  std::unique_ptr<correction::CorrectionSet> cset_;
  std::string working_point_;
  std::string period_;
};

#endif