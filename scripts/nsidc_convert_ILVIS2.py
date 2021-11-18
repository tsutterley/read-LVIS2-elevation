#!/usr/bin/env python
u"""
nsidc_convert_ILVIS2.py
Written by Tyler Sutterley (11/2021)

Reads IceBridge Geolocated LVIS Elevation Product datafiles directly
    from NSIDC server as bytes and outputs as HDF5 files

https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python
https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-
    https-earthdata-login-enabled
http://www.voidspace.org.uk/python/articles/authentication.shtml#base64

Register with NASA Earthdata Login system:
https://urs.earthdata.nasa.gov

Add NSIDC_DATAPOOL_OPS to NASA Earthdata Applications
https://urs.earthdata.nasa.gov/oauth/authorize?client_id=_JLuwMHxb2xX6NwYTb4dRA

CALLING SEQUENCE:
    python nsidc_convert_ILVIS2.py --user <username>
    where <username> is your NASA Earthdata username

COMMAND LINE OPTIONS:
    --help: list the command line options
    -Y X, --year X: years to sync
    -S X, --subdirectory X: specific subdirectories to sync
    -U X, --user X: username for NASA Earthdata Login
    -D X, --directory: working data directory
    -V, --verbose: Verbose output of files synced
    -C, --clobber: Overwrite existing data in transfer
    -M X, --mode X: Local permissions mode of the directories and files synced

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python
        https://numpy.org
    h5py: Python interface for Hierarchal Data Format 5 (HDF5)
        https://www.h5py.org/
    lxml: Pythonic XML and HTML processing library using libxml2/libxslt
        https://lxml.de/
        https://github.com/lxml/lxml
    future: Compatibility layer between Python 2 and Python 3
        http://python-future.org/

UPDATE HISTORY:
    Updated 11/2021: use argparse for command line options
    Updated 10/2021: using python logging for handling verbose output
    Updated 12/2018: decode authorization header for python3 compatibility
    Updated 11/2018: encode base64 strings for python3 compatibility
    Updated 07/2018 for public release
"""
from __future__ import print_function

import sys
import os
import re
import h5py
import netrc
import shutil
import getpass
import logging
import argparse
import builtins
import posixpath
import numpy as np
import calendar, time
import read_LVIS2_elevation.utilities
import read_LVIS2_elevation.convert_julian

#-- PURPOSE: sync the Icebridge LVIS elevation data from NSIDC
def nsidc_convert_ILVIS2(DIRECTORY, YEARS=None, SUBDIRECTORY=None,
    CLOBBER=False, MODE=0o775):
    #-- standard output (terminal output)
    logging.basicConfig(level=logging.INFO)
    #-- Land, Vegetation and Ice Sensor Surface Elevation Product (Level-2)
    #-- remote directories for dataset on NSIDC server
    remote_directories = ["ICEBRIDGE","ILVIS2.001"]
    #-- regular expression for file prefixes of product
    remote_regex_pattern = '(ILVIS2)_(GL|AQ)(\d+)_(\d+)_(R\d+)_(\d+).TXT'

    #-- remote https server for Icebridge Data
    HOST = 'https://n5eil01u.ecs.nsidc.org'
    #-- regular expression operator for finding icebridge-style subdirectories
    if SUBDIRECTORY:
        #-- Sync particular subdirectories for product
        R2 = re.compile('('+'|'.join(SUBDIRECTORY)+')', re.VERBOSE)
    elif YEARS:
        #-- Sync particular years for product
        regex_pattern = '|'.join('{0:d}'.format(y) for y in YEARS)
        R2 = re.compile('({0}).(\d+).(\d+)'.format(regex_pattern), re.VERBOSE)
    else:
        #-- Sync all available years for product
        R2 = re.compile('(\d+).(\d+).(\d+)', re.VERBOSE)
    #-- compile regular expression operator for extracting modification date
    date_regex_pattern = '(\d+)\-(\d+)\-(\d+)\s(\d+)\:(\d+)'
    R3 = re.compile(date_regex_pattern, re.VERBOSE)

    #-- get subdirectories from remote directory
    remote_sub,_,error = read_LVIS2_elevation.utilities.nsidc_list(
        [HOST,remote_directories[0],remote_directories[1]],
        pattern=R2,sort=True)
    #-- print if subdirectory was not found
    if not remote_sub:
        logging.critical(error)
        return
    #-- for each remote subdirectory
    for sd in remote_sub:
        #-- check if data directory exists and recursively create if not
        local_dir = os.path.join(DIRECTORY,sd)
        os.makedirs(local_dir,MODE) if not os.path.exists(local_dir) else None
        #-- find Icebridge data files
        colnames,collastmod,error = read_LVIS2_elevation.utilities.nsidc_list(
            [HOST,remote_directories[0],remote_directories[1],sd],
            pattern=remote_regex_pattern, sort=True)
        #-- print if file was not found
        if not colnames:
            logging.critical(error)
            continue
        #-- sync each Icebridge data file
        for colname,remote_mtime in zip(colnames,collastmod):
            #-- remote and local versions of the file
            remote_file = posixpath.join([HOST,remote_directories[0],
                remote_directories[1],sd,colname])
            local_file = os.path.join(local_dir,colname)
            http_pull_file(remote_file, remote_mtime, local_file,
                CLOBBER=CLOBBER, MODE=MODE)

#-- PURPOSE: pull file from a remote host checking if file exists locally
#-- and if the remote file is newer than the local file
#-- read the input file and output as HDF5
def http_pull_file(remote_file, remote_mtime, local_file,
    CLOBBER=False, MODE=0o775):
    #-- split extension from input LVIS data file
    fileBasename, fileExtension = os.path.splitext(local_file)
    #-- copy Level-2 file from server into new HDF5 file
    if (fileExtension == '.TXT'):
        local_file = '{0}.H5'.format(fileBasename)
    #-- if file exists in file system: check if remote file is newer
    TEST = False
    OVERWRITE = ' (clobber)'
    #-- check if local version of file exists
    if os.access(local_file, os.F_OK):
        #-- check last modification time of local file
        local_mtime = os.stat(local_file).st_mtime
        #-- if remote file is newer: overwrite the local file
        if (remote_mtime > local_mtime):
            TEST = True
            OVERWRITE = ' (overwrite)'
    else:
        TEST = True
        OVERWRITE = ' (new)'
    #-- if file does not exist locally, is to be overwritten, or CLOBBER is set
    if TEST or CLOBBER:
        #-- Printing files transferred
        logging.info('{0} --> '.format(remote_file))
        logging.info('\t{0}{1}\n'.format(local_file,OVERWRITE))
        #-- Download xml files using shutil chunked transfer encoding
        if (fileExtension == '.xml'):
            #-- Create and submit request. There are a wide range of exceptions
            #-- that can be thrown here, including HTTPError and URLError.
            request = read_LVIS2_elevation.utilities.urllib2.Request(remote_file)
            response = read_LVIS2_elevation.utilities.urllib2.urlopen(request)
            #-- chunked transfer encoding size
            CHUNK = 16 * 1024
            #-- copy contents to local file using chunked transfer encoding
            #-- transfer should work properly with ascii and binary data formats
            with open(local_file, 'wb') as f:
                shutil.copyfileobj(response, f, CHUNK)
        else:
            #-- read input data
            LVIS_L2_input,LDS_VERSION = read_LVIS_file(remote_file)
            HDF5_icebridge_lvis(LVIS_L2_input, LDS_VERSION, FILENAME=local_file,
                INPUT_FILE=remote_file)
        #-- keep remote modification time of file and local access time
        os.utime(local_file, (os.stat(local_file).st_atime, remote_mtime))
        os.chmod(local_file, MODE)

#-- PURPOSE: read the LVIS Level-2 data file for variables of interest
def read_LVIS_file(remote_file):
    #-- regular expression pattern for extracting parameters from new format of
    #-- LVIS2 files (format for LDS 1.04 and 2.0+)
    regex_pattern = '(ILVIS2)_(GL|AQ)(\d+)_(\d{2})(\d{2})_(R\d+)_(\d+).TXT$'
    #-- extract mission, region and other parameters from filename
    MISSION,REGION,YY,MM,DD,RLD,SS = re.findall(regex_pattern,remote_file).pop()
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

    #-- Create and submit request. There are a wide range of exceptions
    #-- that can be thrown here, including HTTPError and URLError.
    request = read_LVIS2_elevation.utilities.urllib2.Request(remote_file)
    f = read_LVIS2_elevation.utilities.urllib2.urlopen(request)
    #-- read icebridge LVIS dataset
    file_contents = [i for i in f.read().splitlines() if re.match('^(?!#)',i)]
    #-- compile regular expression operator for reading lines (extracts numbers)
    rx = re.compile('[-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?')
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
            val = np.array(line_contents[i], dtype=file_dtype['formats'][i])
            LVIS_L2_input[key][line_number] = val
    #-- calculation of julian day (not including hours, minutes and seconds)
    year,month,day = np.array([YY,MM,DD],dtype=np.float)
    JD = calc_julian_day(year,month,day)
    #-- converting to J2000 seconds and adding seconds since start of day
    LVIS_L2_input['J2000'] = (JD - 2451545.0)*86400.0 + LVIS_L2_input['Time']
    #-- return the output variables
    return (LVIS_L2_input, LDS_VERSION)

#-- PURPOSE: calculate the Julian day from calendar date
#-- http://scienceworld.wolfram.com/astronomy/JulianDate.html
def calc_julian_day(YEAR, MONTH, DAY, HOUR=0, MINUTE=0, SECOND=0):
    JD = 367.*YEAR - np.floor(7.*(YEAR + np.floor((MONTH+9.)/12.))/4.) - \
        np.floor(3.*(np.floor((YEAR + (MONTH - 9.)/7.)/100.) + 1.)/4.) + \
        np.floor(275.*MONTH/9.) + DAY + 1721028.5 + HOUR/24. + MINUTE/1440. + \
        SECOND/86400.
    return np.array(JD,dtype=np.float)

#-- PURPOSE: output HDF5 file with geolocated elevation surfaces calculated
#-- from LVIS Level-1b waveform products
def HDF5_icebridge_lvis(ILVIS2_MDS,LDS_VERSION,FILENAME=None,INPUT_FILE=None):
    #-- open output HDF5 file
    fileID = h5py.File(FILENAME, 'w')

    #-- create sub-groups within HDF5 file
    fileID.create_group('Time')
    fileID.create_group('Geolocation')
    fileID.create_group('Elevation_Surfaces')
    #-- sub-groups specific to the LDS version 2.0.2
    if (LDS_VERSION == '2.0.2'):
        fileID.create_group('Waveform')
        fileID.create_group('Instrument_Parameters')

    #-- Dimensions of parameters
    n_records, = ILVIS2_MDS['Shot_Number'].shape

    #-- Defining output HDF5 variable attributes
    attributes = {}
    #-- LVIS_LFID
    attributes['LVIS_LFID'] = {}
    attributes['LVIS_LFID']['long_name'] = 'LVIS Record Index'
    attributes['LVIS_LFID']['description'] = ('LVIS file identification, '
        'including date and time of collection and file number. The third '
        'through seventh values in first field represent the Modified Julian '
        'Date of data collection.')
    #-- Shot Number
    attributes['Shot_Number'] = {}
    attributes['Shot_Number']['long_name'] = ('Shot Number')
    attributes['Shot_Number']['description'] = ('Laser shot assigned during '
        'collection')
    #-- Time
    attributes['Time'] = {}
    attributes['Time']['long_name'] = 'Transmit time of each shot'
    attributes['Time']['units'] = 'Seconds'
    attributes['Time']['description'] = 'UTC decimal seconds of the day'
    #-- J2000
    attributes['J2000'] = {}
    attributes['J2000']['long_name'] = ('Transmit time of each shot in J2000 '
        'seconds')
    attributes['J2000']['units'] = 'seconds since 2000-01-01 12:00:00 UTC'
    attributes['J2000']['description'] = ('The transmit time of each shot in '
        'the 1 second frame measured as UTC seconds elapsed since Jan 1 '
        '2000 12:00:00 UTC.')
    #-- Centroid
    attributes['Longitude_Centroid'] = {}
    attributes['Longitude_Centroid']['long_name'] = 'Longitude_Centroid'
    attributes['Longitude_Centroid']['units'] = 'Degrees East'
    attributes['Longitude_Centroid']['description'] = ('Corresponding longitude '
        'of the LVIS Level-1B waveform centroid')
    attributes['Latitude_Centroid'] = {}
    attributes['Latitude_Centroid']['long_name'] = 'Latitude_Centroid'
    attributes['Latitude_Centroid']['units'] = 'Degrees North'
    attributes['Latitude_Centroid']['description'] = ('Corresponding latitude of '
        'the LVIS Level-1B waveform centroid')
    attributes['Elevation_Centroid'] = {}
    attributes['Elevation_Centroid']['long_name'] = 'Elevation_Centroid'
    attributes['Elevation_Centroid']['units'] = 'Meters'
    attributes['Elevation_Centroid']['description'] = ('Elevation surface of the '
        'LVIS Level-1B waveform centroid')
    #-- Lowest mode
    attributes['Longitude_Low'] = {}
    attributes['Longitude_Low']['long_name'] = 'Longitude_Low'
    attributes['Longitude_Low']['units'] = 'Degrees East'
    attributes['Longitude_Low']['description'] = ('Longitude of the '
        'lowest detected mode within the LVIS Level-1B waveform')
    attributes['Latitude_Low'] = {}
    attributes['Latitude_Low']['long_name'] = 'Latitude_Low'
    attributes['Latitude_Low']['units'] = 'Degrees North'
    attributes['Latitude_Low']['description'] = ('Latitude of the '
        'lowest detected mode within the LVIS Level-1B waveform')
    attributes['Elevation_Low'] = {}
    attributes['Elevation_Low']['long_name'] = 'Elevation_Low'
    attributes['Elevation_Low']['units'] = 'Meters'
    attributes['Elevation_Low']['description'] = ('Mean Elevation of the '
        'lowest detected mode within the LVIS Level-1B waveform')
    #-- Highest mode
    attributes['Longitude_High'] = {}
    attributes['Longitude_High']['long_name'] = 'Longitude_High'
    attributes['Longitude_High']['units'] = 'Degrees East'
    attributes['Longitude_High']['description'] = ('Longitude of the '
        'highest detected mode within the LVIS Level-1B waveform')
    attributes['Latitude_High'] = {}
    attributes['Latitude_High']['long_name'] = 'Latitude_High'
    attributes['Latitude_High']['units'] = 'Degrees North'
    attributes['Latitude_High']['description'] = ('Latitude of the '
        'highest detected mode within the LVIS Level-1B waveform')
    attributes['Elevation_High'] = {}
    attributes['Elevation_High']['long_name'] = 'Elevation_High'
    attributes['Elevation_High']['units'] = 'Meters'
    attributes['Elevation_High']['description'] = ('Mean Elevation of the '
        'highest detected mode within the LVIS Level-1B waveform')
    #-- Highest detected signal
    attributes['Longitude_Top'] = {}
    attributes['Longitude_Top']['long_name'] = 'Longitude_Top'
    attributes['Longitude_Top']['units'] = 'Degrees East'
    attributes['Longitude_Top']['description'] = ('Longitude of the '
        'highest detected signal within the LVIS Level-1B waveform')
    attributes['Latitude_Top'] = {}
    attributes['Latitude_Top']['long_name'] = 'Latitude_Top'
    attributes['Latitude_Top']['units'] = 'Degrees North'
    attributes['Latitude_Top']['description'] = ('Latitude of the '
        'highest detected signal within the LVIS Level-1B waveform')
    attributes['Elevation_Top'] = {}
    attributes['Elevation_Top']['long_name'] = 'Elevation_Top'
    attributes['Elevation_Top']['units'] = 'Meters'
    attributes['Elevation_Top']['description'] = ('Mean Elevation of the '
        'highest detected signal within the LVIS Level-1B waveform')
    #-- heights at which a percentage of the waveform energy occurs
    pv = [10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,96,97,98,99,100]
    for RH in pv:
        attributes['RH{0:d}'.format(RH)] = {}
        attributes['RH{0:d}'.format(RH)]['long_name'] = 'RH{0:d}'.format(RH)
        attributes['RH{0:d}'.format(RH)]['units'] = 'Meters'
        attributes['RH{0:d}'.format(RH)]['description'] = ('Height relative to '
            'the lowest detected mode at which {0:d}%  of the waveform '
            'energy occurs').format(RH)
    #-- Laser parmeters
    #-- Azimuth
    attributes['Azimuth'] = {}
    attributes['Azimuth']['long_name'] = 'Azimuth'
    attributes['Azimuth']['units'] = 'degrees'
    attributes['Azimuth']['description'] = 'Azimuth angle of the laser beam.'
    attributes['Azimuth']['valid_min'] = 0.0
    attributes['Azimuth']['valid_max'] = 360.0
    #-- Incident Angle
    attributes['Incident_Angle'] = {}
    attributes['Incident_Angle']['long_name'] = 'Incident_Angle'
    attributes['Incident_Angle']['units'] = 'degrees'
    attributes['Incident_Angle']['description'] = ('Off-nadir incident angle '
        'of the laser beam.')
    attributes['Incident_Angle']['valid_min'] = 0.0
    attributes['Incident_Angle']['valid_max'] = 360.0
    #-- Range
    attributes['Range'] = {}
    attributes['Range']['long_name'] = 'Range'
    attributes['Range']['units'] = 'meters'
    attributes['Range']['description'] = ('Distance between the instrument and '
        'the ground.')
    #-- Complexity
    attributes['Complexity'] = {}
    attributes['Complexity']['long_name'] = 'Complexity'
    attributes['Complexity']['description'] = ('Complexity metric for the '
        'return waveform.')
    #-- Flags
    attributes['Flag1'] = {}
    attributes['Flag1']['long_name'] = 'Flag1'
    attributes['Flag1']['description'] = ('Flag indicating LVIS channel used '
        'to locate lowest detected mode.')
    attributes['Flag2'] = {}
    attributes['Flag2']['long_name'] = 'Flag1'
    attributes['Flag2']['description'] = ('Flag indicating LVIS channel used '
        'to calculate RH metrics.')
    attributes['Flag3'] = {}
    attributes['Flag3']['long_name'] = 'Flag1'
    attributes['Flag3']['description'] = ('Flag indicating LVIS channel '
        'waveform contained in Level-1B file.')

    #-- Defining the HDF5 dataset variables
    h5 = {}

    #-- Defining Shot_Number dimension variable
    h5['Shot_Number'] = fileID.create_dataset('Shot_Number', (n_records,),
        data=ILVIS2_MDS['Shot_Number'], dtype=ILVIS2_MDS['Shot_Number'].dtype,
        compression='gzip')
    #-- add HDF5 variable attributes
    for att_name,att_val in attributes['Shot_Number'].items():
        h5['Shot_Number'].attrs[att_name] = att_val

    #-- Time Variables
    for k in ['LVIS_LFID','Time','J2000']:
        v = ILVIS2_MDS[k]
        h5[k] = fileID.create_dataset('Time/{0}'.format(k), (n_records,),
            data=v, dtype=v.dtype, compression='gzip')
        #-- attach dimensions
        h5[k].dims[0].label='Shot_Number'
        h5[k].dims[0].attach_scale(h5['Shot_Number'])
        #-- add HDF5 variable attributes
        for att_name,att_val in attributes[k].items():
            h5[k].attrs[att_name] = att_val

    #-- Geolocation Variables
    if (LDS_VERSION == '1.04'):
        geolocation_keys = ['Longitude_Centroid','Longitude_Low',
            'Longitude_High','Latitude_Centroid','Latitude_Low','Latitude_High']
    elif (LDS_VERSION == '2.0.2'):
        geolocation_keys = ['Longitude_Low','Longitude_High','Longitude_Top',
            'Latitude_Low','Latitude_High','Latitude_Top']
    for k in geolocation_keys:
        v = ILVIS2_MDS[k]
        h5[k] = fileID.create_dataset('Geolocation/{0}'.format(k),
            (n_records,), data=v, dtype=v.dtype, compression='gzip')
        #-- attach dimensions
        h5[k].dims[0].label='Shot_Number'
        h5[k].dims[0].attach_scale(h5['Shot_Number'])
        #-- add HDF5 variable attributes
        for att_name,att_val in attributes[k].items():
            h5[k].attrs[att_name] = att_val

    #-- Elevation Surface Variables
    if (LDS_VERSION == '1.04'):
        elevation_keys = ['Elevation_Centroid','Elevation_Low','Elevation_High']
    elif (LDS_VERSION == '2.0.2'):
        elevation_keys = ['Elevation_Low','Elevation_High','Elevation_Top']
    for k in elevation_keys:
        v = ILVIS2_MDS[k]
        h5[k] = fileID.create_dataset('Elevation_Surfaces/{0}'.format(k),
            (n_records,), data=v, dtype=v.dtype, compression='gzip')
        #-- attach dimensions
        h5[k].dims[0].label='Shot_Number'
        h5[k].dims[0].attach_scale(h5['Shot_Number'])
        #-- add HDF5 variable attributes
        for att_name,att_val in attributes[k].items():
            h5[k].attrs[att_name] = att_val

    #-- variables specific to the LDS version 2.0.2
    if (LDS_VERSION == '2.0.2'):
        #-- Waveform Variables
        height_keys = ['RH10','RH15','RH20','RH25','RH30','RH35','RH40',
            'RH45','RH50','RH55','RH60','RH65','RH70','RH75','RH80','RH85',
            'RH90','RH95','RH96','RH97','RH98','RH99','RH100','Complexity']
        for k in height_keys:
            v = ILVIS2_MDS[k]
            h5[k] = fileID.create_dataset('Waveform/{0}'.format(k),
                (n_records,), data=v, dtype=v.dtype, compression='gzip')
            #-- attach dimensions
            h5[k].dims[0].label='Shot_Number'
            h5[k].dims[0].attach_scale(h5['Shot_Number'])
            #-- add HDF5 variable attributes
            for att_name,att_val in attributes[k].items():
                h5[k].attrs[att_name] = att_val

        #-- instrument parameter variables
        instrument_parameter_keys = ['Azimuth','Incident_Angle','Range','Flag1',
            'Flag2','Flag3']
        for k in instrument_parameter_keys:
            v = ILVIS2_MDS[k]
            h5[k]=fileID.create_dataset('Instrument_Parameters/{0}'.format(k),
                (n_records,), data=v, dtype=v.dtype, compression='gzip')
            #-- attach dimensions
            h5[k].dims[0].label='Shot_Number'
            h5[k].dims[0].attach_scale(h5['Shot_Number'])
            #-- add HDF5 variable attributes
            for att_name,att_val in attributes[k].items():
                h5[k].attrs[att_name] = att_val


    #-- Defining global attributes for output HDF5 file
    fileID.attrs['featureType'] = 'trajectory'
    fileID.attrs['title'] = 'IceBridge LVIS L2 Geolocated Surface Elevation'
    fileID.attrs['comment'] = ('Operation IceBridge products may include test '
        'flight data that are not useful for research and scientific analysis. '
        'Test flights usually occur at the beginning of campaigns. Users '
        'should read flight reports for the flights that collected any of the '
        'data they intend to use')
    fileID.attrs['summary'] = ("Surface elevation measurements over areas "
        "including Greenland and Antarctica. The data were collected as part "
        "of NASA Operation IceBridge funded campaigns.")
    fileID.attrs['references'] = '{0}, {1}'.format('http://lvis.gsfc.nasa.gov/',
        'http://nsidc.org/data/docs/daac/icebridge/ilvis2')
    fileID.attrs['date_created'] = time.strftime('%Y-%m-%d',time.localtime())
    fileID.attrs['project'] = 'NASA Operation IceBridge'
    fileID.attrs['instrument'] = 'Land, Vegetation, and Ice Sensor (LVIS)'
    fileID.attrs['processing_level'] = '2'
    fileID.attrs['elevation_file'] = INPUT_FILE
    #-- LVIS Data Structure (LDS) version
    #-- https://lvis.gsfc.nasa.gov/Data/Data_Structure/DataStructure_LDS104.html
    #-- https://lvis.gsfc.nasa.gov/Data/Data_Structure/DataStructure_LDS202.html
    fileID.attrs['version'] = 'LDSv{0}'.format(LDS_VERSION)
    #-- Geospatial and temporal parameters
    fileID.attrs['geospatial_lat_min'] = ILVIS2_MDS['Latitude_Low'].min()
    fileID.attrs['geospatial_lat_max'] = ILVIS2_MDS['Latitude_Low'].max()
    fileID.attrs['geospatial_lon_min'] = ILVIS2_MDS['Longitude_Low'].min()
    fileID.attrs['geospatial_lon_max'] = ILVIS2_MDS['Longitude_Low'].max()
    fileID.attrs['geospatial_lat_units'] = "degrees_north"
    fileID.attrs['geospatial_lon_units'] = "degrees_east"
    fileID.attrs['geospatial_ellipsoid'] = "WGS84"
    fileID.attrs['time_type'] = 'UTC'
    fileID.attrs['date_type'] = 'J2000'
    #-- convert start and end time from J2000 seconds into Julian days
    J1 = ILVIS2_MDS['J2000'][0]/86400.0 + 2451545.0
    J2 = ILVIS2_MDS['J2000'][-1]/86400.0 + 2451545.0
    #-- convert to calendar date with convert_julian.py
    cal_date = read_LVIS2_elevation.convert_julian(np.array([J1,J2]),ASTYPE='i')
    args = (cal_date['hour'][0],cal_date['minute'][0],cal_date['second'][0])
    fileID.attrs['RangeBeginningTime'] = '{0:02d}:{1:02d}:{2:02d}'.format(*args)
    args = (cal_date['hour'][-1],cal_date['minute'][-1],cal_date['second'][-1])
    fileID.attrs['RangeEndingTime'] = '{0:02d}:{1:02d}:{2:02d}'.format(*args)
    args = (cal_date['year'][0],cal_date['month'][0],cal_date['day'][0])
    fileID.attrs['RangeBeginningDate'] = '{0:4d}:{1:02d}:{2:02d}'.format(*args)
    args = (cal_date['year'][-1],cal_date['month'][-1],cal_date['day'][-1])
    fileID.attrs['RangeEndingDate'] = '{0:4d}:{1:02d}:{2:02d}'.format(*args)
    time_coverage_duration = ILVIS2_MDS['J2000'][-1] - ILVIS2_MDS['J2000'][0]
    fileID.attrs['DurationTime'] ='{0:0.0f}'.format(time_coverage_duration)
    #-- Closing the HDF5 file
    fileID.close()

#-- Main program that calls nsidc_convert_ILVIS2()
def main():
    #-- Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Reads IceBridge Geolocated LVIS Elevation Product
            datafiles directly from NSIDC server as bytes and outputs as
            HDF5 files
            """
    )
    #-- command line parameters
    #-- NASA Earthdata credentials
    parser.add_argument('--user','-U',
        type=str, default=os.environ.get('EARTHDATA_USERNAME'),
        help='Username for NASA Earthdata Login')
    parser.add_argument('--netrc','-N',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.path.join(os.path.expanduser('~'),'.netrc'),
        help='Path to .netrc file for authentication')
    #-- working data directory
    parser.add_argument('--directory','-D',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.getcwd(),
        help='Working data directory')
    #-- years of data to sync
    parser.add_argument('--year','-Y',
        type=int, nargs='+',
        help='Years to sync')
    #-- subdirectories of data to sync
    parser.add_argument('--subdirectory','-S',
        type=str, nargs='+',
        help='subdirectories of data to sync')
    #-- clobber will overwrite the existing data
    parser.add_argument('--clobber','-C',
        default=False, action='store_true',
        help='Overwrite existing data')
    #-- permissions mode of the local directories and files (number in octal)
    parser.add_argument('--mode','-M',
        type=lambda x: int(x,base=8), default=0o775,
        help='permissions mode of output files')
    args,_ = parser.parse_known_args()
    #-- NASA Earthdata hostname
    HOST = 'urs.earthdata.nasa.gov'
    #-- get authentication
    try:
        args.user,_,PASSWORD = netrc.netrc(args.netrc).authenticators(HOST)
    except:
        #-- check that NASA Earthdata credentials were entered
        if not args.user:
            prompt = 'Username for {0}: '.format(HOST)
            args.user = builtins.input(prompt)
        #-- enter password securely from command-line
        prompt = 'Password for {0}@{1}: '.format(args.user,HOST)
        PASSWORD = getpass.getpass(prompt)
    #-- build a urllib opener for NSIDC
    #-- Add the username and password for NASA Earthdata Login system
    opener = read_LVIS2_elevation.utilities.build_opener(args.user,PASSWORD)

    #-- check internet connection before attempting to run program
    #-- check NASA earthdata credentials before attempting to run program
    if read_LVIS2_elevation.utilities.check_credentials():
        nsidc_convert_ILVIS2(args.directory, YEARS=args.year,
            SUBDIRECTORY=args.subdirectory, CLOBBER=args.clobber,
            MODE=args.mode)

#-- run main program
if __name__ == '__main__':
    main()
