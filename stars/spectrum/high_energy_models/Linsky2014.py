import numpy as np

def _f_uv_bins(f_Lya, Mstar=False):
    m = np.array([0.344, 0.309, 0.000, 0.258,
                  0.572, 0.240, 0.518, 0.764, 0.065])
    b = np.array([1.357, 1.300, 0.882, 2.294,
                  2.098, 1.920, 1.894, 1.811, 1.004])
    if Mstar:
        m[:3] = [0.000, 0.000, 0.000]
        b[:3] = [0.491, 0.548, 0.602]
    return f_Lya*10**(-b+m*np.log10(f_Lya))
f_uv_bins = np.vectorize(_f_uv_bins)

def _f_uv(f_Lya, Mstar=False):
    """
    Defining:
            XUV as 10   to 60   nm
            EUV as 60   to 91.2 nm
            FUV sa 91.2 to 117  nm
    """
    f_bins = f_uv_bins(f_Lya, Mstar)
    XUV = f_bins[0:5].sum()
    EUV = f_bins[5:8].sum()
    FUV = f_bins[8:].sum()
    ion_to_40eV = f_bins[2:8].sum()
    return XUV+EUV
    #return np.array([XUV, EUV, FUV])
f_uv = np.vectorize(_f_uv)


def _n_uv_bins(f_Lya, Mstar=False):
    mean_E = (C_h*C_c) / \
        (np.array([150, 250, 350, 450, 550, 650, 750, 856, 1041])*1e-8)
    return f_uv_bins(f_Lya, Mstar)/mean_E
n_uv_bins = np.vectorize(_n_uv_bins)


def _n_uv(f_Lya, Mstar=False):
    n_bins = n_uv_bins(f_Lya, Mstar)
    XUV = n_bins[0:5].sum()
    EUV = n_bins[5:8].sum()
    FUV = n_bins[8:].sum()
    return np.array([XUV, EUV, FUV])
n_uv = np.vectorize(_n_uv)