#!/usr/bin/env python3

import numpy as np

from ... import constants as const
from ...stars.spectrum import high_energy as McHess # high-energy stellar spectrum
from ...stars.relations import mass_relation as McSmr # stellar mass relation
from ...stars.relations import temperature_relation as McStr # stellar temperatre relation
from ...stars.relations import colour_relation as McScr # stellar colour relation

def _Mc_euv(mass, semimajor, stellar_age, xray='Jackson', euv='Chadney',
            verbose=False, extrapolate=False, shift=False):
    """
    Description:
        For a given stellar mass and age calculates the euv flux at the
        given semimajor axis. Several methods avaiable for calculating the
        euv luminoisty of a star, but currently all first calculate the
        x-ray luminosity.
    
    Arguments:
        mass: mass of star (in solar masses)
        semimajor: distance at which the flux is desired (in centimeters)
        stellar_age: age of star (in years)
        
    Keyword arguments:
        xray: method for determining x-ray luminosity ('Jackson', 'Owen',
                                                       'SanzForcada', 'Tu')
        euv: method for determining euv luminosity ('blackbody', 'Chadney',
                                                    'SanzForcada')
        verbose: print debugging info (boolean)
        extrapolate: if methods should extrapolate outside their fitted data
        
    Returns:
        euv flux at orbital distance of planet (in erg/s/cm**2 = mW/m**2)
    """
    # Generate an Eker star given a mass
    radius = McSmr.Eker_mass_radius(mass, shift=shift)*const.Rsun
    bolometric_lum = McSmr.Eker_mass_luminosity(mass, shift=shift)*const.Lsun
    T_eff = McSmr.Eker_mass_temperature(mass, shift=shift)
    # Get intrinsic B-V colour
    BV0 = McStr.Ballesteros_teff_to_BV(T_eff)
    # Calculate x-ray luminosity
    if xray == 'Jackson':
        # Caclulate x-ray luminosity using Jackson's result
        xray_lum = McHess.Jackson_xray_fraction(BV0, stellar_age,
                                                extrapolate=extrapolate)
        xray_lum = xray_lum*bolometric_lum
    elif xray == 'Owen':
        # Uses Jackson's model with rough round numbers that work across colour bins
        # and solar fitted time dependent power-law index
        xray_lum = 10**(-3.5)*bolometric_lum
        if stellar_age > 1e8:
            xray_lum *= (stellar_age/1e8)**(-1.5)
    elif xray == 'SanzForcada':
        xray_lum = McHess.SanzForcada_xray_luminosity(bolometric_lum,
                                                      stellar_age)
    elif xray == 'Tu':
        # Get rotation rate at 1 Megayear
        rot_period_Myr = McScr.Mamajek_rotation_rate(BV0, 1e6,
                                                     extrapolate=extrapolate)
        rot_rate_Myr = (2*const.pi)/(rot_period_Myr)
        xray_lum = McHess.Tu_xray_luminosity(rot_rate_Myr, stellar_age)
    else:
        print("Do not recognize method '{:s}' for calculating x-ray luminosity"
              .format(xray))
        return -1
    # Calculate euv luminosity
    if euv == 'blackbody':
        euv_surface_flux = McHess.bb_euv_surface_flux(T_eff)
        euv_lum = (4*const.pi*radius**2)*euv_surface_flux
    elif euv == 'Chadney':
        xray_surface_flux = xray_lum/(4*const.pi*radius**2)
        euv_surface_flux = McHess.Chadney_euv_surface_flux(xray_surface_flux)
        euv_lum = (4*const.pi*radius**2)*euv_surface_flux
    elif euv == 'SanzForcada':
        euv_lum = McHess.SanzForcada_euv_luminosity(xray_lum)
    else:
        print("Do not recoginze method '{:s}'for calculating euv luminosity"
              .format(euv))
        return -1
    # Check if user wants debugging print out
    if verbose:
        print('Rad: {:e} Rsun\nBol: {:e} Lsun\nTemp: {:e} K\nB–V: {:e}\n'
              'L_x: {:e} Lsun\nL_euv: {:e}'
              .format(radius/const.Rsun, bolometric_lum/const.Lsun, T_eff, BV0,
                      xray_lum/const.Lsun, euv_lum/const.Lsun))
    # return euv flux at the planet's location
    return euv_lum/(4*const.pi*semimajor**2)
Mc_euv = np.vectorize(_Mc_euv)