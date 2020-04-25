#!/usr/bin/env python3

# Source paper: Tu et al. 2015 (2015A&A...577L...3T)

import numpy as np

def _xray_luminosity(rot_rate, stellar_age):
    """
    Description:
        Uses Equation 3 of Tu et al. 2015 to calculate a x-ray
        luminosity given the rotation rate and age of the star.
        
    Notes:
        ^Fitted for solar type star (mass and radius)
        ^Tu gives the solar rotation rate as 2.9e−6 rad/s
        ^X-ray defined as wavelengths from 5–100 Angstrom
    
    Arguments:
        rot_rate: rotation rate of star at 1 Megayear (in rad/s)
        stellar_age: age of star (in years)

    Returns:
        x-ray luminosity (in erg/s)
    
    Source paper:
        Sanz-Forcada et al. 2011 (2011A&A...532A...6S)
    """
    sol_rot_rate = 2.9e-6
    rot_rate = rot_rate/sol_rot_rate
    t_sat = 2.9e6*(rot_rate**1.14)
    if stellar_age < t_sat:
        L_x = 10.0**(30.46)
    else:
        solar_Lx_Tu = 10.0**(27.2)
        solar_age_Tu = 4.57e9
        b = 1.0/(0.35*np.log10(rot_rate)-0.98)
        L_x = solar_Lx_Tu*(stellar_age/solar_age_Tu)**b
    return L_x
xray_luminosity = np.vectorize(_xray_luminosity)