#!/usr/bin/env python3

# Source paper: Jackson et al. 2012 (2012MNRAS.422.2024J)

import numpy as np
from scipy.optimize import curve_fit

def _exp_fit(x, a, b, c):
    return a * np.exp(-b * x) + c


#B–V min, B–V max, # stars, log(L_x/L_bol), log(tau_sat), alpha
_Table2 = [
    [0.290, 0.450, 67,  -4.28, 7.87, 1.22],
    [0.450, 0.565, 97,  -4.24, 8.35, 1.24],
    [0.565, 0.675, 92,  -3.67, 7.84, 1.13],
    [0.675, 0.790, 79,  -3.71, 8.03, 1.28],
    [0.790, 0.935, 109, -3.36, 7.90, 1.40],
    [0.935, 1.275, 220, -3.35, 8.28, 1.09],
    [1.275, 1.410, 55,  -3.14, 8.21, 1.18]
]

_bin_mean = [(x[0]+x[1])/2. for x in _Table2]
_log_L_sat = [x[3] for x in _Table2]
_log_tau_sat = [x[4] for x in _Table2]
_alpha = [x[5] for x in _Table2]

# Fits to smooth Jackson's data
_L_sat_popt, _L_sat_pcov = curve_fit(_exp_fit, _bin_mean, _log_L_sat)
_log_tau_sat_avg = np.average(np.asarray(_log_tau_sat))
_alpha_avg = np.average(np.asarray(_alpha))

def _xray_fraction(BV0, stellar_age, extrapolate=False):
    """
    Description:
        Uses Jackson et al. 2012 to estimate the x-ray luminosity as a
        fraction of the bolometric luminosity for a star given the B–V
        colour, and stellar age. If no age is given we assume that star is
        young and is saturated.
        
    Notes:
        ^Jackson's results valid for 0.29 < B-V < 1.41
        ^Use fitted curve for saturation fraction, average for alpha and tau_sat
    
    Arguments:
        BV0: intrinsic B-V colour (in magnitudes)
        stellar_age: age of star (in years)
        
    Keyword arguments:
        extrapolate: extrapolate outside fitted colour range (boolean)
        
    Returns:
        fraction of x-ray luminosity in terms of the bolometric luminosity.
             
    Source paper:
        Jackson et al. 2012 (2012MNRAS.422.2024J)
    """
    if BV0 < _bin_mean[0]:
        if extrapolate or BV0 >= _Table2[0][0]:
            L_XoB = 10**_log_L_sat[0]
        else:
            print("Warning: B-V color {:e} is outside of Jackson's data... "
                  "Smallest B-V data point: {:e}".format(BV0, _Table2[0][0]))
            return -1
    elif BV0 > _bin_mean[-1]:
        if extrapolate or BV0 <= _Table2[-1][1]:
            L_XoB = 10**_log_L_sat[-1]
        else:
            print("Warning: B-V color {:e} is outside of Jackson's data... "
                  "Largest B-V data point: {:e}".format(BV0, _Table2[-1][1]))
            return -1
    else:
        L_XoB = 10**_exp_fit(BV0, *_L_sat_popt)
    L_XoB = min(max(L_XoB, 10**_log_L_sat[0]), 10**_log_L_sat[-1])
    tau_sat = 10**_log_tau_sat_avg
    alpha = _alpha_avg
    if stellar_age > tau_sat:
        L_XoB *= (stellar_age/tau_sat)**(-alpha)
    return L_XoB
xray_fraction = np.vectorize(_xray_fraction)