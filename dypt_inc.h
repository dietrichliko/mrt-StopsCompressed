#ifndef DYPT_INC_H_
#define DYPT_INC_H_
#include <cmath>
// Transverse momentum of lepton pair 
// Usage: pt = pt_lep_met(lep_pt, lep_phi)
template<typename T>
float TransverseMomentum(const T & pt, const T & phi)
{
    float px = Sum(pt * cos(phi));
    float py = Sum(pt * sin(phi));
    return sqrt(px*px+ py*py);
}
#endif