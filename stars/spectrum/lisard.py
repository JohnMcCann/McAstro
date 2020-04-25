import os
import io
import pandas as pd
from datetime import datetime

import utils.constants as const
import utils.timedate as timedate
from utils.data_download import request_content

_lisard_directory = (os.path.dirname(os.path.abspath(__file__))
                     +'/lisard_spectrums/')

# LISARD website and LATIS API
_lisard_url = 'http://lasp.colorado.edu/lisird/'
_latis_url = _lisard_url+'latis/dap/'

# Dailies
_maven_url = 'mvn_euv_l3_daily'
_see_url = 'timed_see_ssi_l3'
_eve_url = 'sdo_eve_ssi_1nm_l3'
_fism_url = 'fism_p_ssi_earth'
_fism2_url = 'fism_daily_hr'

_maven_date_func = timedate.UT_to_str
_see_date_func = timedate.YYYYDDD_to_str
_eve_date_func = timedate.YYYYDDD_to_str
_fism_date_func = timedate.UT_to_str
_fism2_date_func = timedate.YYYYDDD_to_str

_col_type1 = ['date', 'wl', 'F_wl', 'model_unc', 'total_unc']
_col_type2 = ['date', 'wl', 'F_wl', 'unc']
_maven_cols = _col_type1
_see_cols = _col_type2
_eve_cols = _col_type2
_fism_cols = _col_type1
_fism2_cols = _col_type2

_missions = {'maven':(_maven_url, _maven_cols, _maven_date_func),
             'see':(_see_url, _see_cols, _see_date_func),
             'eve':(_eve_url, _eve_cols, _eve_date_func),
             'fism':(_fism_url, _fism_cols, _fism_date_func),
             'fism2':(_fism2_url, _fism2_cols, _fism2_date_func)}

class lisard_spectrum:
    def __init__(self, mission='fism2', date='2009-07-19', sort_values='nu',
                 update=False):
        self.mission = mission
        if self.mission not in _missions.keys():
            print('Unknown mission, requires adding backend.')
            return
        date = list(map(int, date.split('-')))
        mission_filename = _lisard_directory+mission
        if mission == 'fism2':
            decade = date[0]-date[0]%10
            filters = ['&time>={}-01-01T'.format(decade),
                       '&time<{}-01-01T'.format(decade+10)]
            mission_filename += '_'+str(decade)
        else:
            filters = None
        mission_filename += '.parquet'
        mission_url, mission_cols, date_func = _missions[mission]
        if not os.path.exists(_lisard_directory):
            os.makedirs(lisard_directory, exist_ok=True)
        if update or not os.path.isfile(mission_filename):
            url = _latis_url+mission_url+'.csv'
            if filters is not None:
                url += '?'
                for f in filters:
                    url += f
            mission_csv = request_content(url)
            self.data = pd.read_csv(io.BytesIO(mission_csv))
            # Fix LISARD column names
            print(f'Changing {self.data.columns} to {mission_cols}.')
            self.data.columns = mission_cols
            # change nm to cm
            self.data['wl'] = self.data['wl']*1e-7
            self.data['nu'] = const.c/self.data['wl']
            # change seconds since unix epoch to julian date
            self.data['date'] = (
                date_func(self.data['date'].values, fmt='%Y-%m-%d')
            )
            self.data['date'] = pd.to_datetime(self.data['date'],
                                               format='%Y-%m-%d')
            # change W/m^2/nm to erg/s/cm^3
            self.data['F_wl'] = self.data['F_wl']*1e10
            self.data['F_nu'] = self.data['F_wl']*self.data['wl']**2/const.c
            self.data.to_parquet(mission_filename, index=False)
        else:
            self.data = pd.read_parquet(mission_filename)
        self.date_min = self.data.iloc[0]['date']
        self.date_max = self.data.iloc[-1]['date']
        date = datetime(*date)
        if date < self.date_min or date > self.date_max:
            print(f'Date given, {date.strftime("%Y-%m-%d")}, outside of '
                  f'{self.mission} date range.\n'
                  f'  Data date range: [{self.date_min.strftime("%Y-%m-%d")}, '
                  f'{self.date_max.strftime("%Y-%m-%d")}].')
            return
        self.data = self.data.loc[self.data['date']==date]
        self.data.drop('date', axis=1, inplace=True)
        self.data.reset_index(drop=True, inplace=True)
        # Drop bad data points
        self.data = self.data.loc[self.data['F_wl'] > 0]
        self.data = self.data.sort_values('wl')
        self.wl_min = self.data.iloc[0]['wl']
        self.wl_max = self.data.iloc[-1]['wl']
        if sort_values != 'wl':
            self.data = self.data.sort_values(sort_values)