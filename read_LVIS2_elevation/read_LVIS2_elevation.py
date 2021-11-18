#!/usr/bin/env python
u"""
read_LVIS2_elevation.py
Written by Tyler Sutterley (11/2021)

Reads Operation IceBridge LVIS and LVIS Global Hawk Level-2 data products
    provided by the National Snow and Ice Data Center
    http://nsidc.org/data/docs/daac/icebridge/ilvis2/
    http://lvis.gsfc.nasa.gov/OIBDataStructure.html
    http://nsidc.org/data/docs/daac/icebridge/ilvgh2/

Can be the following file types:
    ILVIS2: IceBridge LVIS Level-2 Geolocated Surface Elevation Product
    ILVGH2: IceBridge LVIS-GH Level-2 Geolocated Surface Elevation Product

OUTPUTS LDSv1.04:
    LVIS_LFID:        LVIS file identification, including date and time of
        collection and file number. The second through sixth values in the
        first field represent the Modified Julian Date of data collection
    Shot_Number:        Laser shot assigned during collection
    Time:                UTC decimal seconds of the day
    Longitude_Centroid:    Centroid longitude from corresponding Level-1B waveform
    Latitude_Centroid:    Centroid latitude from corresponding Level-1B waveform
    Elevation_Centroid:    Centroid elevation from corresponding Level-1B waveform
    Longitude_Low:    Longitude of the lowest detected mode within the waveform
    Latitude_Low:    Latitude of the lowest detected mode within the waveform
    Elevation_Low:    Elevation of the lowest detected mode within the waveform
    Longitude_High:    Longitude of the highest detected mode in the waveform
    Latitude_High:    Latitude of the highest detected mode in the waveform
    Elevation_High:    Elevation of the highest detected mode in the waveform
    Time_J2000:        Time converted to seconds since 2000-01-01 12:00:00 UTC

OUTPUTS LDSv2.0.2:
    LFID:            LVIS File Identification
    shotnumber:        Laser shot number assigned during collection
    time:            UTC decimal seconds of the day
    glon:            Longitude of the lowest detected mode within the waveform
    glat:            Latitude of the lowest detected mode within the waveform
    zg:                Mean elevation of the lowest detected mode within the waveform
    tlon:            Longitude of the highest detected signal
    tlat:            Latitude of the highest detected signal
    zt:                Elevation of the highest detected signal
    hlon:            Longitude of the center of the highest mode within the waveform
    hlat:            Latitude of the center of the highest mode within the waveform
    zh:                Mean elevation of the highest mode within the waveform
    RH10:            Height above zg at which 10%  of the waveform energy occurs
    RH15:            Height above zg at which 15%  of the waveform energy occurs
    RH20:            Height above zg at which 20%  of the waveform energy occurs
    RH25:            Height above zg at which 25%  of the waveform energy occurs
    RH30:            Height above zg at which 30%  of the waveform energy occurs
    RH35:            Height above zg at which 35%  of the waveform energy occurs
    RH40:            Height above zg at which 40%  of the waveform energy occurs
    RH45:            Height above zg at which 45%  of the waveform energy occurs
    RH50:            Height above zg at which 50%  of the waveform energy occurs
    RH55:            Height above zg at which 55%  of the waveform energy occurs
    RH60:            Height above zg at which 60%  of the waveform energy occurs
    RH65:            Height above zg at which 65%  of the waveform energy occurs
    RH70:            Height above zg at which 70%  of the waveform energy occurs
    RH75:            Height above zg at which 75%  of the waveform energy occurs
    RH80:            Height above zg at which 80%  of the waveform energy occurs
    RH85:            Height above zg at which 85%  of the waveform energy occurs
    RH90:            Height above zg at which 90%  of the waveform energy occurs
    RH95:            Height above zg at which 95%  of the waveform energy occurs
    RH96:            Height above zg at which 96%  of the waveform energy occurs
    RH97:            Height above zg at which 97%  of the waveform energy occurs
    RH98:            Height above zg at which 98%  of the waveform energy occurs
    RH99:            Height above zg at which 99%  of the waveform energy occurs
    RH100:            Height above zg at which 100%  of the waveform energy occurs
    azimuth:        Azimuth angle of the laser beam
    incidentangle:    Off-nadir incident angle of the laser beam
    range:            Distance between the instrument and the ground
    Complexity:        Complexity metric for the return waveform
    Flag1:            Flag indicating LVIS channel used to locate zg
    Flag2:            Flag indicating LVIS channel used calculate RH metrics
    Flag3:            Flag indicating LVIS channel waveform contained in Level1B file

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python
        https://numpy.org
        https://numpy.org/doc/stable/user/numpy-for-matlab-users.html

UPDATE HISTORY:
    Updated 11/2021: use file insensitive case for parsing filenames
    Updated 06/2018: can read and output LVIS LDS version 2.0.2 (2017 campaign+)
    Written 10/2017 for public release
"""
from __future__ import print_function

import os
import re
import copy
import numpy as np

#-- PURPOSE: read the LVIS Level-2 data file for variables of interest
def read_LVIS2_elevation(input_file, SUBSETTER=None):
    #-- regular expression pattern for extracting parameters from new format of
    #-- LVIS2 files (format for LDS 1.04 and 2.0+)
    regex_pattern = ('(BLVIS2|BVLIS2|ILVIS2|ILVGH2)_(GL|AQ)(\d+)_(\d{2})(\d{2})'
        '_(R\d+)_(\d+).TXT$')
    #-- extract mission, region and other parameters from filename
    MISSION,REGION,YY,MM,DD,RLD,SS=re.findall(regex_pattern,input_file,re.I).pop()
    LDS_VERSION = '2.0.2' if (np.int(RLD[1:3]) >= 18) else '1.04'
    #-- input file column types for ascii format LVIS files
    #-- https://lvis.gsfc.nasa.gov/Data/Data_Structure/DataStructure_LDS104.html
    #-- https://lvis.gsfc.nasa.gov/Data/Data_Structure/DataStructure_LDS202.html
    if (LDS_VERSION == '1.04'):
        file_dtype = {}
        file_dtype['names'] = ('LVIS_LFID','Shot_Number','Time',
            'Longitude_Centroid','Latitude_Centroid','Elevation_Centroid',
            'Longitude_Low','Latitude_Low','Elevation_Low',
            'Longitude_High','Latitude_High','Elevation_High')
        file_dtype['formats']=('i','i','f','f','f','f','f','f','f','f','f','f')
    elif (LDS_VERSION == '2.0.2'):
        file_dtype = {}
        file_dtype['names'] = ('LVIS_LFID','Shot_Number','Time',
            'Longitude_Low','Latitude_Low','Elevation_Low',
            'Longitude_Top','Latitude_Top','Elevation_Top',
            'Longitude_High','Latitude_High','Elevation_High',
            'RH10','RH15','RH20','RH25','RH30','RH35','RH40','RH45','RH50',
            'RH55','RH60','RH65','RH70','RH75','RH80','RH85','RH90','RH95',
            'RH96','RH97','RH98','RH99','RH100','Azimuth','Incident_Angle',
            'Range','Complexity','Flag1','Flag2','Flag3')
        file_dtype['formats'] = ('i','i','f','f','f','f','f','f','f','f','f',
            'f','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f','f',
            'f','f','f','f','f','f','f','f','f','f','f','i','i','i')
    #-- read icebridge LVIS dataset
    with open(input_file,'r') as f:
        file_contents=[i for i in f.read().splitlines() if re.match('^(?!#)',i)]
    #-- compile regular expression operator for reading lines (extracts numbers)
    rx = re.compile( '[-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?')
    #-- subset the data to indices if specified
    if SUBSETTER:
        file_contents = [file_contents[i] for i in SUBSETTER]
    #-- output python dictionary with variables
    LVIS_L2_input = {}
    #-- create output variables with length equal to the number of file lines
    for key,val in zip(file_dtype['names'],file_dtype['formats']):
        LVIS_L2_input[key] = np.zeros_like(file_contents, dtype=val)
    #-- for each line within the file
    for line_number,line_entries in enumerate(file_contents):
        #-- find numerical instances within the line
        line_contents = rx.findall(line_entries)
        #-- for each variable of interest: save to dinput as float
        for i,key in enumerate(file_dtype['names']):
            LVIS_L2_input[key][line_number] = line_contents[i]
    #-- calculation of julian day (not including hours, minutes and seconds)
    year,month,day = np.array([YY,MM,DD], dtype=np.float)
    JD = calc_julian_day(year,month,day)
    #-- converting to J2000 seconds and adding seconds since start of day
    LVIS_L2_input['J2000'] = (JD - 2451545.0)*86400.0 + LVIS_L2_input['Time']
    #-- save LVIS version
    LVIS_L2_input['LDS_VERSION'] = copy.copy(LDS_VERSION)
    #-- return the output variables
    return LVIS_L2_input

#-- PURPOSE: calculate the Julian day from calendar date
#-- http://scienceworld.wolfram.com/astronomy/JulianDate.html
def calc_julian_day(YEAR, MONTH, DAY, HOUR=0, MINUTE=0, SECOND=0):
    JD = 367.*YEAR - np.floor(7.*(YEAR + np.floor((MONTH+9.)/12.))/4.) - \
        np.floor(3.*(np.floor((YEAR + (MONTH - 9.)/7.)/100.) + 1.)/4.) + \
        np.floor(275.*MONTH/9.) + DAY + 1721028.5 + HOUR/24. + MINUTE/1440. + \
        SECOND/86400.
    return np.array(JD,dtype=np.float)
