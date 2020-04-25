#!/usr/bin/env python3

# Source paper: Chadney et al. 2015 (2015Icar..250..357C)

def euv_surface_flux(F_x):
    """
    Description:
        Given the x-ray surface flux, Chadney et al. give a relation to the
        euv flux. Note that flux is used instead of luminosity given the
        luminosities dependence on radius. If you wanted an euv luminosity,
        first convert to a surface flux, and then back to a luminosity after
        using Chadney's relationship.
    
    Arguments:
        F_x: stellar surface x-ray flux (in erg/s/cm**2)

    Returns:
        stellar surface euv flux (in erg/s/cm**2)
    
    Source paper:
        Chadney et al. 2015 (2015Icar..250..357C)
    """
    return 425*(F_x**0.58)