import math
# Constants (cgs)
pi = math.pi
## Physical Constants (source: NIST)
e = 4.8032068e-10      # elemtary charge (esu)
c = 2.99792458e10      # speed of light (cm/s)
h = 6.6260755e-27      # Planck's constant (erg*s)
Ry = 2.1798741e-11     # Rydberg constant (erg)
kB = 1.380658e-16      # Boltzmann's constant (erg/K)
me = 9.1093897e-28     # mass of electron (g)
mp = 1.672621923e-24   # mass of proton (g) [CODATA 2018]
mH = 1.6733e-24        # mass of hydrogen (g)
eV = 1.6021772e-12     # electron volt (erg)
G = 6.67259e-8         # Newton's graviational constant (cm**3/g/s**2)
## Unit conversions
ns = 1.0e-9                 # nanosecond (s)
day = 8.64e4                # Julian day (s)
year = 3.15576e7            # Julian year (s)
srday = 8.616409054e4       # sidereal day (s)
sryear = srday*3.6525636e2  # sidereal year (s)
AA = 1.0e-8                 # Angstrom (cm)
au = 1.496e13               # astronomical unit (cm)
pc = 3.086e18               # parsec (cm)
Mb = 1.0e-18                # megabarn (cm**2)
bar = 1.0e6                 # bar (barye)
Da = 1.66053906660e-24      # Dalton (g)
## Derived Constants
hc = h*c
a0 = h**2./(4.*math.pi**2.*me*e**2.)        # Bhor radius (cm)
sig_SB = 2*math.pi**5*kB**4/(15*c**2*h**3)  # Stefan-Boltzmann constant (erg/cm**2/s/K**4)
RyH = mp/(me+mp)*Ry                         # Hydrogen Rydberg constant (erg)
## Clestial bodies values (source: IAU)
Rjupiter = 7.1492e9      # nominal equatorial Jovian radius (cm)
Mjupiter = 1.8985234e30  # Jovain mass (g)
Rearth = 6.3781366e8     # nominal equatorial Earth radius (cm)
Mearth = 5.9721864e27    # Earth mass (g)
Rsun = 6.96e10           # nominal equatorial Solar radius (cm)
Msun = 1.9884159e33      # Solar mass (g)
Lsun = 3.828e33          # Solar bolometric luminosity (erg/s/cm**2)
EUVearth = 450           # Earth EUV flux (erg/s/cm**2)
1.361
## Lyman Alpha (Doublet Mean, source: NIST ASD)
Lya_wl = 1215.67e-8  # wavelength (cm)
Lya_nu = c/Lya_wl    # frequency (1/s)
Lya_f12 = .4164      # oscillator strength
Lya_gamma = 6.265e8  # natural broadening frequency (1/s)