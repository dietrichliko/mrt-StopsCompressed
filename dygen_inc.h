#ifndef DYPT_INC_H_
#define DYPT_INC_H_
#include <cmath>
#include <set>

#include <string>
#include <sstream>
#include <iomanip>

/// Convert integer value `val` to text in hexadecimal format.
/// The minimum width is padded with leading zeros; if not 
/// specified, this `width` is derived from the type of the 
/// argument. Function suitable from char to long long.
/// Pointers, floating point values, etc. are not supported; 
/// passing them will result in an (intentional!) compiler error.
/// Basics from: http://stackoverflow.com/a/5100745/2932052
template <typename T>
inline std::string int_to_hex(T val, size_t width=sizeof(T)*2)
{
    std::stringstream ss;
    ss << std::setfill('0') << std::setw(width) << std::hex << (val|0);
    return ss.str();
}

float GenDY_pt(
    const ROOT::RVecF & pt,
    const ROOT::RVecF & eta,
    const ROOT::RVecF & phi,
    const ROOT::RVecF & mass,
    const ROOT::RVecI & pdgId, 
    const ROOT::RVecI & status, 
    const ROOT::RVecI & statusFlags)
{
    std::set<int> leptons { 11, 13, 15 };

    int l1 = -1;
    int l2 = -1;
    for (size_t i = 0; i<pt.size(); i++ )
    {
        if ((statusFlags[i] & 0x1181) == 0x1181 ) {
            if (l1 == -1 && leptons.find(abs(pdgId[i])) != leptons.end())
            {
                l1 = i;
            } else if (pdgId[i] == - pdgId[l1]) {
                l2 = i;
            }           
        }         
    }
    float dy_pt = -1.;
    if ( l2 > 0) {
        if (min(pt[l1], pt[l2]) > 15. && max(pt[l1], pt[l2]) > 40 && abs(eta[l1])<1.5 && abs(eta[l2])<1.5) {
            auto v1 = ROOT::Math::PtEtaPhiMVector(pt[l1], eta[l1], phi[l1], mass[l1]);
            auto v2 = ROOT::Math::PtEtaPhiMVector(pt[l2], eta[l2], phi[l2], mass[l2]);
            dy_pt = (v1+v2).Pt();
        }
    } else {
        std::cout << "Not all leptons found" << std::endl;
    }
    return dy_pt;
}

float GenDY_mass(
    const ROOT::RVecF & pt,
    const ROOT::RVecF & eta,
    const ROOT::RVecF & phi,
    const ROOT::RVecF & mass,
    const ROOT::RVecI & pdgId, 
    const ROOT::RVecI & status, 
    const ROOT::RVecI & statusFlags)
{
    std::set<int> leptons { 11, 13, 15 };

    // int event_type = 0;
    // int z =  -1;
    int l1 = -1;
    int l2 = -1;
    for (size_t i = 0; i<pt.size(); i++ )
    {
        if ((statusFlags[i] & 0x1181) == 0x1181 ) {
            if (l1 == -1 && leptons.find(abs(pdgId[i])) != leptons.end())
            {
                l1 = i;
            } else if (pdgId[i] == - pdgId[l1]) {
                l2 = i;
            }           
        } 
    }
//    std::cout << "Found" << z << " " << l1 << " " << l2 << std::endl;
    float m = -1.;
    if ( l2 > 0 ) {
        if (min(pt[l1], pt[l2]) > 15. && max(pt[l1], pt[l2]) > 40) {
            auto v1 = ROOT::Math::PtEtaPhiMVector(pt[l1], eta[l1], phi[l1], mass[l1]);
            auto v2 = ROOT::Math::PtEtaPhiMVector(pt[l2], eta[l2], phi[l2], mass[l2]);
            m = (v1+v2).M();
        }        
    } else {
        std::cout << "not all leptons found" << std::endl;
    }
    return m;
}

#endif