from .high_energy_models import (Chadney2015, Jackson2012, Linsky2014,
                                 SanzForcada2011, Tu2015)
from .black_body import BlackBody

__all__ = []

def Chadney_euv_surface_flux(F_x):
    return Chadney2015.euv_surface_flux(F_x)
Chadney_euv_surface_flux.__doc__ = (Chadney2015.euv_surface_flux.__doc__)
__all__ += ['Chadney_euv_surface_flux']

def Jackson_xray_fraction(BV0, stellar_age, extrapolate=False):
    return Jackson2012.xray_fraction(BV0, stellar_age, extrapolate=extrapolate)
Jackson_xray_fraction.__doc__ = (Jackson2012._xray_fraction.__doc__)
__all__ += ['Jackson_xray_fraction']


def SanzForcada_euv_luminosity(L_x):
    return SanzForcada2011.euv_luminosity(L_x)
SanzForcada_euv_luminosity.__doc__ = (
    SanzForcada2011.euv_luminosity.__doc__)
__all__ += ['SanzForcada_euv_luminosity']


def SanzForcada_xray_luminosity(L_bol, stellar_age):
    return SanzForcada2011.xray_luminosity(L_bol, stellar_age)
SanzForcada_xray_luminosity.__doc__ = (
    SanzForcada2011._xray_luminosity.__doc__)
__all__ += ['SanzForcada_xray_luminosity']


def Tu_xray_luminosity(rot_rate, stellar_age):
    return Tu2015.xray_luminosity(rot_rate, stellar_age)
Tu_xray_luminosity.__doc__ = (Tu2015._xray_luminosity.__doc__)
__all__ += ['Tu_xray_luminosity']

def Linsky_euv(f_Lya):
    return Linsky2014.f_uv(f_Lya)


def bb_euv_surface_flux(T_eff):
    m0, b0, T0 = 0.655635, 1106.224278, 2300.000000
    m1, b1, T1 = 0.733707, 3204.257429, 5500.000000
    m2, b2, T2 = 0.915299, 5625.490934, 8800.000000
    m3, b3, T3 = 0.744415, 9012.095703, 12500.000000
    if T_eff < T0:
        T_euv = b0*T_eff/T0
    elif T_eff < T1:
        T_euv = m0*(T_eff-T0)+b0
    elif T_eff < T2:
        T_euv = m1*(T_eff-T1)+b1
    elif T_eff < T3:
        T_euv = m2*(T_eff-T2)+b2
    else:
        T_euv = m3*(T_eff-T3)+b3
    return BlackBody(T_euv).spec_integral(lob=1e-8, upb=912e-8)