#!/usr/bin/env python3

import math, copy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
cc = plt.rcParams['axes.prop_cycle'].by_key()['color']
from scipy import integrate, interpolate
from scipy.signal import savgol_filter
from scipy.interpolate import Akima1DInterpolator

from McAstro.utils import constants as const
from McAstro.stars.spectrum.lisird import lisird_spectrum
from McAstro.atoms.atomic_species import atomic_species

class species:
    def __init__(self):
        self.atomic_data = None
        self.sigma = None
        self.I_ion = None
        self.threshold_wl = None


class glq_spectrum:
    """
    Description:
        Class for calculating the Gauss-Legendre quadrature dataponts of
        the ionization and heating rates of a stellar spectrum in an
        atmosphere comprised of the given absorbing species.
        
        Order of operation is to create a glq_rates object, then add the
        consitutients of the atmosphere with add_species(). Next the
        spectrum should be subbinned with subbin(). Following the max
        degree of the polynomial needed to approximate the rates is
        calculated by calling get_max_degree(). Then the GLQ datapoints
        are set by calling set_abscissas(). The data can be saved to a
        csv with write_csv().
    """
    def __init__(self, mission='fism2', date='2002-01-01', wl_norm=1e-7):
        """
        Keyword arguments:
            mission: name of the lisird data set to fetch data from
            date: The date of the stellar observations (format: %Y-%m-%d)
            wl_norm: Normalizes the wavelength, which is in cm if wl_norm=1
        """
        # Stellar "Observation" info
        self.mission = mission
        self.date = date
        # Observed spectrum
        spectrum = lisird_spectrum(mission=mission, date=date, sort_values='wl')
        self.spectrum = spectrum
        self.data = spectrum.data
        self.data['E'] = const.hc/self.data['wl']
        self.data['Phi_wl'] = self.data['F_wl']/self.data['E']
        self.data['bin'] = -1*np.ones(len(self.data), dtype=int)
        # Data in normalized units
        self.data_norm = self.data.copy()
        self.data_norm.drop(columns='unc', inplace=True)
        self.data_norm.rename(columns={'F_wl':'f_wl', 'Phi_wl':'phi_wl'},
                              inplace=True)
        # Convert wavelength to nm
        self.wl_norm = wl_norm # convert cm to nm
        self.data_norm['wl'] /= self.wl_norm
        self.spectrum.wl_min /= self.wl_norm
        self.spectrum.wl_max /= self.wl_norm
        # Convert Energy to eV
        self.E_norm = const.eV
        self.data_norm['E'] /= self.E_norm
        # Normalize spectral energy flux
        self.F_tot = integrate.simps(self.data['F_wl'], self.data['wl'])
        self.F_rslv = integrate.simps(self.data['F_wl'], self.data['wl'])
        self.data_norm['f_wl'] *= self.wl_norm/self.F_rslv
        # Normalize spectral number flux
        # To relate phi_wl to f_wl always use E in cgs not hc/wl_norm or E in eV
        # or phi_wl = (E_mean/E) * f_wl, where E_mean = F_tot/Phi_tot
        self.Phi_tot = integrate.simps(self.data['Phi_wl'], self.data['wl'])
        self.Phi_rslv = integrate.simps(self.data['Phi_wl'], self.data['wl'])
        self.data_norm['phi_wl'] *= self.wl_norm/self.Phi_rslv
        # Composition of atmosphere
        self.n_species = 0
        self.species_list = []
        # Binning of spectrum
        self.n_bins = 1
        self.bin_breaks = np.array([self.spectrum.wl_min, self.spectrum.wl_max])
        self.species_breaks = np.array([])
        # Smoothing of spectrum and polynomial fitting
        self.interp, self.n_passes, self.E_mean, self.f_poly, self.poly_deg = (
            [None] for i in range(5)
        )
        self.subbin_breaks, self.crits, self.n_crits = (
            [None] for i in range(3)
        )
        # Gaussian Quadrature
        self.max_degree = None
        self.bin_absc, self.bin_wgts = ([None] for i in range(2))
        # Spans
        self.wndw_span = None
        self.rslv_span = None
        self.norm_span = None


    def add_species(self, species_name):
        """
        Description:
            Adds a species to be considering the analysis of the spectrum.
            Ionization edges subdivide the spectrum, and the wavelength
            dependence of the cross section is also taken into account. The
            species are recognized by their spectrospecy names, meaning the
            element symbol and ionization stage as a Roman numeral, e.g.,
            neutral hydrogen is 'H I', singly ionized helium is 'He II', and
            quadruply ionized oxygen is 'O V'. Verner et al. 1996
            (1996ApJ...465..487V) is used for the atmoic data, see
            McAstro.atoms.
            
        Arguments:
            species_name: The spectrospecy name of the species, e.g., 'C IV'
        """
        # Add to species list
        for species_obj in self.species_list:
            if species_obj.atomic_data.name == species_name:
                print('WARNING: Species already in list, returning.')
                return
        new_atomic_data = atomic_species(species_name)
        if new_atomic_data.verner_data is None:
            return
        new_species = species()
        new_species.atomic_data = new_atomic_data
        new_species.sigma = (
            new_atomic_data.cross_section(self.data['E']/const.eV)
        )
        new_species.I_ion = new_atomic_data.verner_data['E_th']*const.eV
        new_species.threshold_wl = const.hc/new_species.I_ion
        new_species.threshold_wl /= self.wl_norm
        self.species_list.append(new_species)
        # Add species edge to species breaks
        if len(self.species_breaks) == 0:
            self.species_breaks = np.array([new_species.threshold_wl])
        else:
            self.species_breaks = (
                np.concatenate((np.array([new_species.threshold_wl]),
                                self.species_breaks))
            )
            self.species_breaks.sort()
        # Add species edge to binning
        if new_species.threshold_wl not in self.bin_breaks:
            self.bin_spectrum(list(self.bin_breaks)+[new_species.threshold_wl])
        self.n_species += 1
        # Smooth updated spectrum
        self.truncate_spectrum()


    def remove_species(self, species_name):
        """
        Description:
            Removes a species that had been previous added for tracking, see
            add_species().
            
        Arguments:
            species_name: The spectrospecy name of the species, e.g., 'C IV'
        """
        # Remove from species list
        old_species = None
        for species_obj in self.species_list:
            if species_obj.atomic_data.name == species_name:
                old_species = species_obj
                continue
        if old_species is None:
            print('ERROR: Failed to find species in list.')
            return
        self.species_list.remove(old_species)
        # Remove species edge from species breaks
        old_bin_break = const.hc/old_species.I_ion
        old_bin_break /= self.wl_norm
        self.species_breaks = np.array(
            list(self.species_breaks).remove(old_bin_break)
        )
        self.species_breaks.sort()
        # Remove species edge from binning
        if old_bin_break in self.bin_breaks:
            self.bin_breaks = list(self.bin_breaks)
            self.bin_breaks.remove(old_bin_break)
            self.bin_spectrum(self.bin_breaks)
        self.n_species -= 1
        # Smooth updated spectrum
        self.truncate_spectrum()


    def truncate_spectrum(self, wl_min=None, wl_max=None):
        """
        Description:
            Truncates the spectrum to the region of interest (ROI), either
            that specified by the arguments or based on the species tracked.
            By default wl_max is not specified so it is assumed to be that
            of the lowest ionization threshold of the tracked species.
            
        Keyword arguments:
            wl_min: lower wavelength bound for ROI (in wl_norm)
            wl_max: upper wavelength bound for ROI (in wl_norm)
        """
        # if wl_max is none use lowest ionization potential
        if wl_max is None:
            if len(self.species_list) < 1:
                print('ERROR: Can only truncate bins if given list of species.')
                return
            min_I_ion = np.inf
            for species_obj in self.species_list:
                if species_obj.I_ion < min_I_ion:
                    min_I_ion = species_obj.I_ion
            wl_max = const.hc/min_I_ion
            wl_max /= self.wl_norm
        # Reinclude all species breaks in case they were previously truncated
        self.bin_breaks = np.asarray(list(self.bin_breaks)
                                     +list(self.species_breaks))
        self.bin_breaks = np.unique(self.bin_breaks)
        self.bin_breaks.sort()        
        # Determine the new bin breaks by dropping all outside [wl_min, wl_max]
        new_breaks = list(self.bin_breaks)
        if self.bin_breaks[-1] != wl_max:
            if wl_max not in self.bin_breaks:
                new_breaks += [wl_max]
            new_breaks.sort()
            edge_index = new_breaks.index(wl_max)
            new_breaks = new_breaks[:edge_index+1]
        if wl_min is not None:
            if wl_min not in self.bin_breaks:
                new_breaks += [wl_min]
            new_breaks.sort()
            edge_index = new_breaks.index(wl_min)
            new_breaks = new_breaks[edge_index:]
        # Drop non-species breaks within 0.1 nm of a species break
        # including wl_min/max
        new_breaks = np.asarray(new_breaks)
        for sbreak in self.species_breaks:
            mk = ((abs(new_breaks-sbreak)>=0.1*(1e-7/self.wl_norm))
                  |(new_breaks==sbreak))
            new_breaks = new_breaks[mk]
        # Check that edges are duplicated
        if (len(new_breaks) > 1 and
            abs(new_breaks[0]-new_breaks[1])/new_breaks[0] < 1e-5):
            new_breaks = new_breaks[1:]
        if (len(new_breaks) > 1 and
            abs(new_breaks[-1]-new_breaks[-2])/new_breaks[-1] < 1e-5):
            new_breaks = new_breaks[:-1]
        # Bin the spectrum and smooth
        self.bin_spectrum(new_breaks)


    def add_bin_edge(self, bin_edge):
        self.bin_breaks.sort()
        new_breaks = list(self.bin_breaks)
        if bin_edge not in self.bin_breaks:
            new_breaks += [bin_edge]
        new_breaks.sort()
        # Bin the spectrum and smooth
        self.bin_spectrum(new_breaks)
        self.smooth_spectrum()
        return


    def bin_spectrum(self, bin_breaks):
        """
        Description:
            Given the bin edges of the spectrum it sanitizes the list and
            sets the bin breaks.
        
        Arguments:
            bin_breaks: List of bin breaks (in wl_norm)
        """
        try: # Put ints and floats into list
            bin_breaks[0]
        except (TypeError, IndexError):
            bin_breaks = [bin_breaks]
        bin_breaks = np.asarray(bin_breaks)
        if bin_breaks.size == 1: # monochromatic
            self.n_bins = 0
            self.bin_breaks = bin_breaks
            return
        bin_breaks.sort()
        self.bin_breaks = bin_breaks
        self.n_bins = len(bin_breaks)-1
        # Check bins
        for b in range(self.n_bins):
            if (self.spectrum.wl_min > bin_breaks[b]
                or self.spectrum.wl_max < bin_breaks[b+1]):
                print("WARNING: Mission's spectrum does not span "
                      "requested bin's wavelengths.")
                print(f'        ({self.mission}) wavelegnth span: '
                      f'[{self.spectrum.wl_min:.2f}, '
                      f'{self.spectrum.wl_max:.2f}] nm')
                print('WARNING: Truncating binning to fit mission spectrum.')
                if bin_breaks[b+1] < self.spectrum.wl_min:
                    self.bin_breaks = self.bin_breaks[1:]
                    self.n_bins -= 1
                    continue
                elif bin_breaks[b] > self.spectrum.wl_max:
                    self.bin_breaks = self.bin_breaks[:b]
                    self.n_bins = len(self.bin_breaks)-1
                    break
                elif bin_breaks[b] < self.spectrum.wl_min:
                    self.bin_breaks[0] = self.spectrum.wl_min
                elif bin_breaks[b+1] > self.spectrum.wl_max:
                    dropped_bins = len(bin_breaks)-1-self.n_bins
                    last_bin = b+1-dropped_bins
                    self.bin_breaks[last_bin] = self.spectrum.wl_max
                    self.bin_breaks = self.bin_breaks[:last_bin+1]
                    self.n_bins = len(self.bin_breaks)-1
                    break
                else:
                    print('ERROR: This should be impossible...\n'
                          '       Time for debugging!')
                    return
        self.interp, self.n_passes, self.E_mean, self.f_poly, self.poly_deg = (
            [None,]*self.n_bins for i in range(5)
        )
        self.subbin_breaks, self.crits, self.n_crits = (
            [None,]*self.n_bins for i in range(3)
        )


    def smooth_spectrum(self, n_passes=10, savgol_window=21, savgol_degree=1,
                        desired_degree=None, lsq_err=1e-3, crit_dist=None,
                        d2_crits=True, conserve_phi=True):
        """
        Description:
            Smooths the spectrum by running the spectrum through multiple
            passes of a Savitzky–Golay filter. The continuity of the
            spectrum is broken by subdividing the spectrum along ionization
            edges, so that no energy leaks into a species that it shouldn't.
            The each smoothed sub-spectrum is renormalized to conserve the
            total energy of that sub-spectrum.
        
        Keyword arguments:
            n_passes: The number of passes in the multipass filtering
            savgol_window: datapoints used in Savitzky-Golay filter
            savgol_degree: Degree of Savitzky-Golay filter polynomial
            desired_degree: Smooth until a polynomial of desired degree fits
            lsq_err: Least-Squares error tolerance of polynomial fit
            crit_dist: Minimum distance between critical points
            d2_crits: Add second derivative roots to critical points
            conserve_phi: Conserve Phi if True, else conserve F
            norm_span: Sets the normalization span, defaults to ROI
            rslv_span: Sets the resolved span, defaults to ROI
        """
        # Reset bin id to -1
        self.data_norm.loc[:, 'bin'] = -1*np.ones(len(self.data), dtype=int)
        # Error check
        if self.n_bins == 0: # Monochromatic
            return
        # Select smoothing variable
        if conserve_phi:
            smth_var = 'phi_wl_smth'
            var = 'phi_wl'
            othr_var = 'f_wl_smth'
        else:
            smth_var = 'f_wl_smth'
            var = 'f_wl'
            othr_var = 'phi_wl_smth'
        # Smooth spectrum
        for n in range(self.n_bins):
            mk = ((self.data_norm['wl']>=self.bin_breaks[n])
                  &(self.data_norm['wl']<=self.bin_breaks[n+1]))
            # Set bin id
            self.data_norm.loc[mk, 'bin'] = n
            # Calculate bin fraction
            frac = integrate.simps(self.data_norm[var][mk],
                                   self.data_norm['wl'][mk])
            # First Savitzky-Golay filter pass
            self.data_norm.loc[mk, smth_var] = (
                savgol_filter(self.data_norm.loc[mk, var],
                              savgol_window, savgol_degree)
                )
            # Perform multipass Savitzky-Golay filter based on desired result
            if desired_degree is None and crit_dist is None:
                # Smooth based on a set amount of passes
                for p in range(n_passes-1):
                    self.data_norm.loc[mk, smth_var] = (
                        savgol_filter(self.data_norm[smth_var][mk],
                                      savgol_window, savgol_degree)
                    )
                self.n_passes[n] = n_passes
            elif desired_degree is None:
                # smooth until minimum crit distance found
                self.n_passes[n] = 0
                while True:
                    self.data_norm.loc[mk, smth_var] = (
                        savgol_filter(self.data_norm[smth_var][mk],
                                      savgol_window, savgol_degree)
                    )
                    self.n_passes[n] += 1
                    self.interp[n] = (
                        Akima1DInterpolator(self.data_norm['wl'][mk],
                                            self.data_norm[smth_var][mk])
                    )
                    crits = list(self.interp[n].derivative().roots())
                    if d2_crits:
                        d2_smooth = savgol_filter(
                            self.interp[n].derivative(nu=2)(
                                self.data_norm['wl'][mk]), 11, 1)
                        d2crits = Akima1DInterpolator(self.data_norm['wl'][mk],
                                                      d2_smooth).roots()
                        d2crits = [c for c in d2crits 
                                   if ((c/d2crits[0] > 1.01
                                        and c/d2crits[-1] < 0.99))]
                        crits += d2crits
                    crits.sort()
                    if len(crits) < 2 or np.diff(crits).min() > crit_dist:
                        break
            else:
                # Smooth until fit by a polynomial of desired degree
                self.n_passes[n] = 0
                while True:
                    self.data_norm.loc[mk, smth_var] = (
                        savgol_filter(self.data_norm[smth_var][mk],
                                      savgol_window, savgol_degree)
                    )
                    self.n_passes[n] += 1
                    # Renormalize smooth spectrum, important so poly normalized
                    smth_frac = (
                        integrate.simps(self.data_norm[smth_var][mk],
                                        self.data_norm['wl'][mk])
                    )
                    self.data_norm.loc[mk, smth_var] *= (frac/smth_frac)
                    poly, residual, rank, sv, rcond = (
                        np.polyfit(self.data_norm['wl'][mk],
                                   self.data_norm[smth_var][mk],
                                   desired_degree, full=True)
                    )
                    poly_frac = (
                        integrate.simps(np.polyval(poly,
                                                   self.data_norm['wl'][mk]),
                                        self.data_norm['wl'][mk])
                    )
                    if abs(frac-poly_frac)/frac > 1e-3:
                        continue
                    if not residual.size:
                        # If residual wasn't calculated, calculate my own
                        residual = (
                            ((np.polyval(poly, self.data_norm['wl'][mk])
                              -self.data_norm.loc[mk, smth_var])**2).sum()
                        )
                    if residual < lsq_err:
                        self.f_poly[n] = poly
                        break
            # Renormalize smooth spectrum
            normalization = (
                frac/integrate.simps(self.data_norm[smth_var][mk],
                                     self.data_norm['wl'][mk]),
            )
            self.data_norm.loc[mk, smth_var] *= normalization
            # Calculate E_mean
            self.E_mean[n] = (
                integrate.simps(self.data['F_wl'][mk], self.data['wl'][mk])
                /integrate.simps(self.data['Phi_wl'][mk], self.data['wl'][mk])
            )
            # Generate an interpolation function
            self.interp[n] = (
                Akima1DInterpolator(self.data_norm['wl'][mk],
                                    self.data_norm[smth_var][mk])
            )            
            self.crits[n] = list(self.interp[n].derivative().roots())
            self.n_crits[n] = len(self.crits[n])
            self.crits[n] = [self.bin_breaks[n], *self.crits[n],
                             self.bin_breaks[n+1]]
        # Smooth other variable that wasn't explictly smoothed
        mk = (self.data_norm['bin']!=-1)
        if conserve_phi:
            self.data_norm.loc[mk, 'f_wl_smth'] = (
                self.data_norm['phi_wl_smth']
                *(self.Phi_tot/self.F_tot)*self.data['E']
            )[mk]
        else:
            self.data_norm.loc[mk, 'phi_wl_smth'] = (
                self.data_norm['f_wl_smth']
                *self.F_tot/(self.Phi_tot*self.data['E'])
            )[mk]
        return


    def fit_polynomail(self, lsq_err=1e-2, crits_enclosed=None,
                       poly_deg=None, max_degree=50):
        """
        Description:
        
        Keyword arguments:
            lsq_err: least square error criteria for fitted polynomial
            crits_enclosed: Subbins the spectrum based on critical points
            poly_deg: Fixed the polynomial degree (overrides lsq_err)
        """
        # Error check
        if self.interp[0] is None:
            print("ERROR: Need to smooth spectrum first.")
            return
        if self.n_bins == 0: # monochromatic
            return
        # Smoothed spectrum is O(1) on nm scale, scale error accordingly
        lsq_err *= (self.wl_norm/1e-7)**2
        self.poly_deg, self.n_subbins = ([None,]*self.n_bins for i in range(2))
        for b in range(self.n_bins):
            mk = ((self.data_norm['wl']>=self.bin_breaks[b])
                  &(self.data_norm['wl']<=self.bin_breaks[b+1]))
            # Subbin based on crits_enclosed
            if crits_enclosed is not None and self.n_crits[b] >= crits_enclosed:
                perfect_fit = (self.n_crits[b]+1)%(crits_enclosed+1)
                n_polys = int((self.n_crits[b]+1)/(crits_enclosed+1)
                             +((self.n_crits[b]+1)-2)/self.n_crits[b])
                self.f_poly[b] = [None,]*n_polys
                self.subbin_breaks[b] = [None,]*n_polys
                for sb in range(len(self.subbin_breaks[b])):
                    self.subbin_breaks[b][sb] = self.crits[b][sb*(crits_enclosed+1)]
                self.subbin_breaks[b] += [self.crits[b][-1]]
                self.n_subbins[b] = len(self.subbin_breaks[b])-1
                self.poly_deg[b] = [None,]*self.n_subbins[b]
            else:
                self.f_poly[b] = [None]
                self.subbin_breaks[b] = [self.bin_breaks[b],
                                         self.bin_breaks[b+1]]
                self.n_subbins[b] = 1
                self.poly_deg[b] = [None]
            # Fit polynomial in all subbins
            if poly_deg is not None:
                for sb in range(self.n_subbins[b]):
                    smk = ((self.data_norm['wl']>=self.subbin_breaks[b][sb])
                           &(self.data_norm['wl']<=self.subbin_breaks[b][sb+1]))
                    self.poly_deg[b][sb] = poly_deg
                    self.f_poly[b][sb], residual, rank, sv, rcond = (
                        np.polyfit(self.data_norm['wl'][smk],
                                   self.interp[b](self.data_norm['wl'][smk]),
                                   poly_deg, full=True)
                    )
            else: # use lsq_err
                for sb in range(self.n_subbins[b]):
                    smk = ((self.data_norm['wl']>=self.subbin_breaks[b][sb])
                           &(self.data_norm['wl']<=self.subbin_breaks[b][sb+1]))
                    try_degree = 1
                    while True:
                        self.f_poly[b][sb], residual, rank, sv, rcond = (
                            np.polyfit(self.data_norm['wl'][smk],
                                       self.interp[b](self.data_norm['wl'][smk]),
                                       try_degree, full=True)
                        )
                        if not residual.size:
                            # If residual wasn't calculated, calculate my own
                            residual = (
                                ((np.polyval(self.f_poly[b][sb],
                                             self.data_norm['wl'][smk])
                                  -self.data_norm.loc[smk, 'phi_wl_smth'])**2).sum()
                            )
                        if residual < lsq_err or try_degree >= max_degree:
                            self.poly_deg[b][sb] = try_degree
                            break
                        else:
                            try_degree += 1
        return


    def set_abscissas(self, window=None, sigma_poly_deg=3, trans_poly_deg=2):
        # Error check
        if window is not None and np.asarray(window).size != 2:
            print('ERROR: Window must of size 2: lower and upper boundaries.')
            return
        if self.n_bins == 0: # monochromatic
            self.wndw_span = None
            return
        # If set to none, set window to span the entire binned spectrum
        if window is None:
            window = np.asarray(self.bin_breaks[0], self.bin_breaks[-1])
        elif window[0] == window[1]:
            self.wndw_span = window
            return
        self.wndw_span = window
        # Set the weights and abscissas
        self.bin_absc, self.bin_wgts, self.interp_norm = (
            [None,]*self.n_bins for i in range(3)
        )
        for b in range(self.n_bins):
            self.bin_absc[b], self.bin_wgts[b] = (
                [None,]*self.n_subbins[b] for i in range(2)
            )
            bmk = ((self.data_norm['wl']>=
                    max(window[0], self.bin_breaks[b]))
                   &(self.data_norm['wl']<=
                     min(window[-1], self.bin_breaks[b+1])))
            # Renormalize interp over this domain to correct smoothing
            self.interp_norm[b] = 1./(
                integrate.simps(self.interp[b](self.data_norm['wl'][bmk]),
                                self.data_norm['wl'][bmk])
            )
            for sb in range(self.n_subbins[b]):
                deg_total = self.poly_deg[b][sb]+sigma_poly_deg+trans_poly_deg
                n_pts = (deg_total+2)//2
                abscissas, weights = np.polynomial.legendre.leggauss(n_pts)
                mk = ((self.data_norm['wl']>=
                       max(window[0], self.subbin_breaks[b][sb]))
                      &(self.data_norm['wl']<=
                        min(window[-1], self.subbin_breaks[b][sb+1])))
                if len(self.data_norm['wl'][mk]) == 0:
                    continue
                # Only set weights and abscissas in window domain else None
                left = self.data_norm['wl'][mk].iloc[0]
                right = self.data_norm['wl'][mk].iloc[-1]
                if left >= right:
                    continue
                diff = (right-left)/2
                avg = (right+left)/2
                self.bin_absc[b][sb] = diff*abscissas+avg
                self.bin_wgts[b][sb] = diff*weights


    def normalize(self, norm_span, rslv_span=None):
        # Error Check
        if np.asarray(norm_span).size != 2:
            print("ERROR: norm_span must have size of 2")
            return
        if rslv_span is None:
            rslv_span = np.asarray(norm_span)
        elif np.asarray(rslv_span).size != 2:
            print("ERROR: rslv_span must have size of 2")
            return
        # Generate mask
        self.norm_span = np.asarray(norm_span)
        mk = ((self.data_norm['wl']>=self.norm_span[0])
              &(self.data_norm['wl']<=self.norm_span[-1]))
        self.rslv_span = np.asarray(rslv_span)
        rmk = ((self.data_norm['wl']>=self.rslv_span[0])
               &(self.data_norm['wl']<=self.rslv_span[-1]))
        # Calculate normalized totals
        self.F_tot = integrate.simps(self.data['F_wl'][mk],
                                     self.data['wl'][mk])
        self.Phi_tot = integrate.simps(self.data['Phi_wl'][mk],
                                       self.data['wl'][mk])
        # Calculate resolved spectrum and normalize f_wl and phi_wl
#         self.data_norm['f_wl'] *= self.F_rslv
        self.F_rslv = integrate.simps(self.data['F_wl'][rmk],
                                      self.data['wl'][rmk])
#         self.data_norm['f_wl'] /= self.F_rslv
#         self.data_norm['phi_wl'] *= self.Phi_rslv
        self.Phi_rslv = integrate.simps(self.data['Phi_wl'][rmk],
                                        self.data['wl'][rmk])
#         self.data_norm['phi_wl'] /= self.Phi_rslv
        self.data_norm['f_wl'] = self.data['F_wl']*self.wl_norm/self.F_rslv
        self.data_norm['phi_wl'] = self.data['Phi_wl']*self.wl_norm/self.Phi_rslv
        # Meta particle stuff?
        self.sigma_mean, self.I_mean = ([None,]*self.n_species
                                        for i in range(2))
        for s, species in enumerate(self.species_list):
            self.sigma_mean[s] = (
                integrate.simps(self.data['Phi_wl'][rmk]*species.sigma[rmk],
                                self.data['wl'][rmk])/self.Phi_rslv
            )
            self.I_mean[s] = (
                integrate.simps(self.data['Phi_wl'][rmk]*species.sigma[rmk]
                                *(const.hc/self.data['wl'][rmk]
                                  -species.I_ion),
                                self.data['wl'][rmk])/self.Phi_rslv
            )
            self.I_mean[s] = (self.F_rslv/self.Phi_rslv
                              -self.I_mean[s]/self.sigma_mean[s])


    def write_csv(self, filename, kind='full', mono_wl=None):
        """
        Description:
            Saves the spectrum data in a format that is readable by the
            relaxation code. Note the relaxation code uses cgs, so variables
            need to be unnormalized.

        Arguments:
            filename: The filename for the spectrum input file

        Keyword arguments:
            kind: Kind of spectrum being saved (full, mono, fixed, or meta)
        """
        # Error check
        if self.interp[0] is None and self.n_bins != 0:
            print('ERROR: First run smooth_spectrum()')
            return
        if self.bin_absc[0] is None and self.n_bins != 0:
            print('ERROR: First run set_abscissas()')
            return
        if kind == 'fixed' and mono_wl is None:
            print('ERROR: For fixed kind, must specify mono wavelength.')
            return
        if kind == 'full' and self.n_bins == 0:
            print('ERROR: Kind cannot be full when n_bins == 0.')
            return
        # Calculate header parameters
        ## Flux to Phi conversion
        if kind == 'fixed':
            if mono_wl != self.wndw_span[0]:
                print('ERROR: If kind is fixed then require mono_wl == window.')
                return
            mean_E = const.hc/(mono_wl*self.wl_norm)
        else:
            mean_E = self.F_rslv/self.Phi_rslv
        FtoPHI = self.Phi_rslv/self.F_tot
        ## Spans: window set in set_abscissas, resolve & normalized in normalize
        if self.wndw_span is None and mono_wl is None:
            print('WARNING: Window span never set, using entire domain.')
            window = np.asarray([self.bin_breaks[0],
                                 self.bin_breaks[-1]])*self.wl_norm
        elif self.wndw_span is None:
            window = mono_wl*self.wl_norm
        else:
            window = self.wndw_span*self.wl_norm
        if self.rslv_span is None:
            print('WARNING: Resolved span never set, using entire domain.')
            resolved = np.asarray([self.bin_breaks[0],
                                   self.bin_breaks[-1]])*self.wl_norm
        else:
            resolved = self.rslv_span*self.wl_norm
        if self.norm_span is None:
            # Not much of a warning, as should always be the case set or not
            print('WARNING: Normalized span never set, using entire domain.')
            normalized = np.asarray([self.bin_breaks[0],
                                     self.bin_breaks[-1]])*self.wl_norm
        else:
            normalized = self.norm_span*self.wl_norm
        # Construct header strings
        headers = [r'$hc/\lambda_i$']
        headers += [r'$w_i\phi_{\lambda_i}$']
        for i, s in enumerate(self.species_list):
            name_nospace = s.atomic_data.name.replace(' ', '')
            headers += [rf'$\sigma_{{\lambda_i,{name_nospace}}}$']
        # Build data table
        if kind != 'full' or self.n_bins == 0: # monochromatic
            binrows = np.array([[mean_E, 1.0]])
            for i, s in enumerate(self.species_list):
                if kind == 'meta':
                    cols = self.sigma_mean[i]
                else:
                    cols = s.atomic_data.cross_section(mean_E/const.eV)
                binrows = np.column_stack([binrows, cols])
            df = pd.DataFrame(binrows, columns=headers)
            df = df.convert_dtypes()
            npts = 1
        else:
            table = []
            npts = 0
            for b in range(self.n_bins):
                for sb in range(self.n_subbins[b]):
                    # Skip subbins that fell outside window and have None
                    if self.bin_absc[b][sb] is None:
                        continue
                    col1 = const.hc/(self.bin_absc[b][sb]*self.wl_norm)
                    hnu = col1/const.eV
                    col2 = (self.bin_wgts[b][sb]*self.interp_norm[b]
                            *self.interp[b](self.bin_absc[b][sb]))
                    binrows = np.column_stack([col1, col2])
                    for i, s in enumerate(self.species_list):
                        cols = s.atomic_data.cross_section(hnu)
                        binrows = np.column_stack([binrows, cols])
                    table.append(binrows)
                    npts += len(self.bin_absc[b][sb])
            table = np.vstack(table)
            df = pd.DataFrame(table, columns=headers)
            df = df.convert_dtypes()
        # Construct header comment
        comment = f'# NPTS: {npts}\n'
        comment += f'# NSPECIES: {self.n_species}\n'
        comment += f'# FtoPHI: {FtoPHI:.17e}\n'
        comment += f'# PHI_FRAC: {1.0:.17e}\n'
        comment += f'# DATE: {self.date}\n'
        comment += f'# KIND: {kind}\n'
        comment += f'# WINDOW: {window[0]:.17e},{window[1]:.17e}\n'
        comment += f'# RESOLVED: {resolved[0]:.17e},{resolved[1]:.17e}\n'
        comment += f'# NORMALIZED: {normalized[0]:.17e},{normalized[1]:.17e}\n'
        comment += '# IONPOTS: '
        for s, species in enumerate(self.species_list):
            if self.n_bins == 0: # monochromatic
                if kind == 'fixed' or kind == 'mono':
                    comment += f'{species.I_ion:.17e}, '
                elif kind == 'meta':
                    comment += f'{self.I_mean[s]:.17e}, '
            else:
                comment += f'{species.I_ion:.17e}, '
        comment = comment[:-2]+'\n# '  
        for h in headers:
            comment += h+', '
        comment = comment[:-2]+'\n'
        # Write to file
        with open(filename, 'w') as file_:
            file_.write(comment)
            df.to_csv(file_, index=False, header=False, float_format='%.17e')
        # Return dataframe that was saved to file
        return df


    def plot(self, plot_polys=False):
        fig, ax = plt.subplots()
        for b in range(self.n_bins):
            for sb in range(self.n_subbins[b]):
                mk = ((self.data_norm['wl']>=self.subbin_breaks[b][sb])
                      &(self.data_norm['wl']<=self.subbin_breaks[b][sb+1]))
                l1, = ax.plot(self.data_norm['wl'][mk],
                              self.data_norm['phi_wl'][mk], lw=1, zorder=0,
                              c=cc[0], label='Spectrum')
                l2, = ax.plot(self.data_norm['wl'][mk],
                              self.data_norm['phi_wl_smth'][mk], lw=5, c=cc[1],
                              label='Smoothed')
                if plot_polys:
                    l3, = ax.plot(self.data_norm['wl'][mk],
                                  np.polyval(self.f_poly[b][sb],
                                             self.data_norm['wl'][mk]), lw=2,
                                  c=cc[2], label='Polyfit')
                v1 = ax.axvline(self.subbin_breaks[b][sb], zorder=-1, c=cc[3],
                                lw=2, ls='--', label='Subbin breaks')
            ax.axvline(self.bin_breaks[b], zorder=0, c=cc[4], lw=2, ls='--')
            for c in range(self.n_crits[b]):
                v2 = ax.axvline(self.crits[b][c], zorder=-2, c=cc[7], lw=2,
                                ls='--', label='Crits')
        v3 = ax.axvline(self.bin_breaks[-1], zorder=0, c=cc[4], lw=2, ls='--',
                        label='Bin breaks')
        ax.set_yscale('log')
        ax.set_xlabel(r'Wavelength ($\lambda$) [nm]')
        ax.set_ylabel('Normalized spectral irradiance\n'
                      r'($\phi_{\nu}$) [cm$^{-2}$ s$^{-1}$ nm$^{-1}$]')
        ax.set_title('Smoothing binning and subbinning')
        fig.tight_layout(pad=0.3)
        fig.subplots_adjust(bottom=0.3, top=0.9)
        lines = [v1, l1, v2, l2, v3]
        if plot_polys:
            lines += [l3]
        labels = [l.get_label() for l in lines]
        fig.legend(lines, labels, bbox_to_anchor=(0.5, 0.0), loc='lower center',
                   ncol=3)
        return fig, ax