#!/usr/bin/env python3

# Source paper: Mamajek & Hillenbrand 2008 (2008ApJ...687.1264M)

import numpy as np

from .... import constants as const

def _rotation_rate(BV0, age, extrapolate=False):
    """
    Description:
        For a given age, turns a B-V colour into a stellar rotation rate.
        
    Notes:
        ^Results were fitted for 0.5 < B-V < 0.9
        ^The fit has a 'color singularity' at 0.495, below which results are
         imaginary. We've patched to give 0, but probably should keep to
         the range of the data fitted
         
    Arguments:
        BV0: intrinsic B-V colour of the star (in magnitudes)
        
    Keyword arguments:
        extrapolate: extrapolate outside fitted colour range (boolean)
        
    Returns:
        Stellar rotation rate (in seconds)
        
    Source paper:
        Mamajek & Hillenbrand 2008 (2008ApJ...687.1264M)
    """
    if (BV0 < 0.5 or BV0 > 0.9):
        if extrapolate:
            if BV0 < 0.495:
                return 0
        else:
            print("Warning: B-V: {:.2f} is outside Mamajek stellar rotation "
                  "fitted range fof 0.5 < B-V < 0.9.".format(BV0))
            return -1
    t = age/1e6
    P_rot = 0.407*(BV0-0.495)**(0.325)*t**(0.566)
    return P_rot*const.day
rotation_rate = np.vectorize(_rotation_rate)