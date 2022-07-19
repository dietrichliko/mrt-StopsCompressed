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
    const ROOT::RVecF & phi,
    const ROOT::RVecI & pdgId, 
    const ROOT::RVecI & status, 
    const ROOT::RVecI & statusFlags)
{
    std::set<int> leptons { 11, 13, 15 };

    int event_type = 0;
    int z =  -1;
    int l1 = -1;
    int l2 = -1;
    for (size_t i = 0; i<pt.size(); i++ )
    {
        if (statusFlags[i] == 0x1181)
        {
            if ( event_type == 0)
            {
                event_type = pdgId[i];
                if (leptons.find(abs(pdgId[i])) != leptons.end()) {
                    l1 = i;
                }
            } 
            if ( event_type == 23 && pdgId[i] == 23)
            {
                z = i;
            } if ( event_type == -pdgId[i]) {
                l2 = i;
            }
        }
    }
    float dy_pt = -1.;
    if ( event_type == 23) 
    {
        dy_pt = pt[z];
        // std::cout << "Z      : " << dy_pt << std::endl; 
    } else if (leptons.find(abs(event_type)) != leptons.end()) 
     {
        dy_pt = -1; 
        // dy_pt = sqrt(pt[l1] * pt[l1] + pt[l2] * pt[l2] + 2 * pt[l1] * pt[l2] * cos(phi[l1]-phi[l2])); 
        // std::cout << "gamma* : " << dy_pt << std::endl;
    } else {
        std::cout << "Unknown event type " << event_type << std::endl;
    }
    return dy_pt;
}
#endif