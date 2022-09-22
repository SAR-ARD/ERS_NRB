NRB_PATTERN = r'^(?P<sensor>ERS[12]|ASAR)_' \
              r'(?P<mode>IMP|IMM|APP|IMS|WSM)_' \
              r'(?P<product>NRB)_' \
              r'(?P<resolution>_)' \
              r'(?P<processingLevel>1)' \
              r'(?P<category>S)' \
              r'(?P<pols>SH|SV|DH|DV|VV|HH|HV|VH)_' \
              r'(?P<start>[0-9]{8}T[0-9]{6})_' \
              r'(?P<stop>[0-9]{8}T[0-9]{6})_' \
              r'(?P<orbitNumber>[0-9]{6})_' \
              r'(?P<dataTakeID>[0-9A-F]{6})'

# Envisat
# FP = FOS predicted orbit state vectors (NRT processing)
# DN = DORIS Level 0 navigator product acquired at PDHS (NRT)
# FR = FOS restituted orbit state vectors
# DI = DORIS initial (preliminary) orbit
# DP = DORIS precise orbit If not used, set to ØØ.    
ORB_MAP = {'PD': 'predicted',
           'RS': 'restituted',
           'PC': 'precise',
           'PL': 'preliminary',
           'FP': 'predicted',
           'DN': 'navigator',
           'FR': 'restituted',
           'DI': 'preliminary',
           'DP': 'precise'}

# ERS-1 IM, ERS-2 IM and ENVISAT IM - Not Applicable
# ENVISAT AP and WS - Not Applied
NOISE_MAP = {'IMS': 'Not Applicable',
             'IMP': 'Not Applicable',
             'IMM': 'Not Applicable',
             'APP': 'Not Applied',
             'APS': 'Not Applied',
             'WSM': 'Not Applied',
}


SAMPLE_MAP = {'-dm.tif': {'type': 'mask',
                          'unit': 'mask',
                          'role': 'data-mask',
                          'title': 'Data Mask Image',
                          'values': {0: 'not layover, nor shadow',
                                     1: 'layover',
                                     2: 'shadow',
                                     3: 'layover and shadow',
                                     4: 'ocean water'}},
              '-ei.tif': {'type': 'angle',
                          'unit': 'deg',
                          'role': 'ellipsoid-incidence-angle',
                          'title': 'Ellipsoid Incidence Angle'},
              '-lc.tif': {'type': 'scattering area',
                          'unit': 'square_meters',
                          'role': 'contributing-area',
                          'title': 'Local Contributing Area'},
              '-li.tif': {'type': 'angle',
                          'unit': 'deg',
                          'role': 'local-incidence-angle',
                          'title': 'Local Incidence Angle'},
              '-gs.tif': {'type': 'ratio',
                          'unit': 'ratio',
                          'role': 'gamma-sigma-ratio',
                          'title': 'Gamma0 RTC to sigma0 RTC ratio'},
              '-id.tif': {'type': 'mask',
                          'unit': None,
                          'role': 'acquisition-id',
                          'title': 'Acquisition ID Image'},
              '-np-vv.tif': {'type': 'noise power VV',
                             'unit': None,
                             'role': 'noise-power',
                             'title': 'Noise Power VV'},
              '-np-vh.tif': {'type': 'noise power VH',
                             'unit': None,
                             'role': 'noise-power',
                             'title': 'Noise Power VH'},
              '-np-hh.tif': {'type': 'noise power HH',
                             'unit': None,
                             'role': 'noise-power',
                             'title': 'Noise Power HH'},
              '-np-hv.tif': {'type': 'noise power HV',
                             'unit': None,
                             'role': 'noise-power',
                             'title': 'Noise Power HV'}}
     