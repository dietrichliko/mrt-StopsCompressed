// gSystem->AddIncludePath("
// -I/groups/hephy/cms/dietrich.liko/conda/envs/mrt/lib/python3.10/site-packages/correctionlib/include");
// gSystem->AddLinkedLibs("-L/groups/hephy/cms/dietrich.liko/conda/envs/mrt/lib/python3.10/site-packages/correctionlib/lib
// -lcorrectionlib");

#include <algorithm>
#include <cmath>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>

#include "correction.h"

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
  ElectronSF(const std::string& cset_file, const std::string& working_point) {
    cset_ = correction::CorrectionSet::from_file(cset_file);
    wp_ = working_point;
    // std::cout << "Electron Corrections" << std::endl;
    // for (auto& corr : *cset_) {
    //   std::cout << "Correction: " << corr.first << std::endl;
    // }
  }
  double operator()(double pt, double eta) const {
    return cset_->at("UL-Electron-ID-SF")
        ->evaluate({"2016preVFP", "sf", wp_, eta, pt});
  }

 private:
  std::unique_ptr<correction::CorrectionSet> cset_;
  std::string wp_;
};

int main() {
  // MuonIds : LooseID, MediumID, TightID and others...
  std::unique_ptr<MuonSF> muonSF;
  muonSF = std::make_unique<MuonSF>(
      "Run2016preVFP",
      "jsonpog-integration/POG/MUO/2016preVFP_UL/muon_Z.json.gz", "MediumID");
  // Electron Working Points : Veto, Loose, Medium, Tight and others...
  // auto elecSF = ElectronSF(
  //     "jsonpog-integration/POG/EGM/2016preVFP_UL/electron.json.gz", "Loose");

  for (double eta : {-1.5, -0.5, 0.5, -1.5}) {
    for (double pt : {15., 25., 35., 45.}) {
      std::cout << "Muon " << pt << ", " << eta << " : " << (*muonSF)(pt, eta)
                << std::endl;
      // std::cout << "Electron " << pt << ", " << eta << " : " << elecSF(pt,
      // eta)
      //           << std::endl;
    }
  }
};
