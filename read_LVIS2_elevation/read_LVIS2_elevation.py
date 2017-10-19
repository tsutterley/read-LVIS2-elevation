#!/usr/bin/env python
u"""
read_LVIS2_elevation.py
Written by Tyler Sutterley (10/2017)

Reads Operation IceBridge LVIS and LVIS Global Hawk Level-2 data products
	provided by the National Snow and Ice Data Center
	http://nsidc.org/data/docs/daac/icebridge/ilvis2/
	http://lvis.gsfc.nasa.gov/OIBDataStructure.html
	http://nsidc.org/data/docs/daac/icebridge/ilvgh2/

Can be the following file types:
	ILVIS2: IceBridge LVIS Level-2 Geolocated Surface Elevation Product
	ILVGH2: IceBridge LVIS-GH Level-2 Geolocated Surface Elevation Product

OUTPUTS:
	LVIS_LFID:		LVIS file identification, including date and time of
		collection and file number. The second through sixth values in the
		first field represent the Modified Julian Date of data collection
	Shot_Number:		Laser shot assigned during collection
	Time:				UTC decimal seconds of the day
	Longitude_Centroid:	Centroid longitude from corresponding Level-1B waveform
	Latitude_Centroid:	Centroid latitude from corresponding Level-1B waveform
	Elevation_Centroid:	Centroid elevation from corresponding Level-1B waveform
	Longitude_Low:	Longitude of the lowest detected mode within the waveform
	Latitude_Low:	Latitude of the lowest detected mode within the waveform
	Elevation_Low:	Elevation of the lowest detected mode within the waveform
	Longitude_High:	Longitude of the highest detected mode in the waveform
	Latitude_High:	Latitude of the highest detected mode in the waveform
	Elevation_High:	Elevation of the highest detected mode in the waveform
	Time_J2000:		Time converted to seconds since 2000-01-01 12:00:00 UTC

PYTHON DEPENDENCIES:
	numpy: Scientific Computing Tools For Python
		http://www.numpy.org
		http://www.scipy.org/NumPy_for_Matlab_Users

UPDATE HISTORY:
	Written 10/2017 for public release
"""
from __future__ import print_function

import os
import re
import numpy as np

#-- PURPOSE: read the LVIS Level-2 data file for variables of interest
def read_LVIS2_elevation(input_file, SUBSETTER=None):
	#-- regular expression pattern for extracting parameters from new format of
	#-- LVIS2 files (reprocessed in 2014)
	mission_flag = '(BLVIS2|BVLIS2|ILVIS2|ILVGH2)'
	regex_pattern='{0}_(.*?)(\d+)_(\d+)_(R\d+)_(\d+).TXT$'.format(mission_flag)
	#-- extract mission, region and other parameters from filename
	MISSION,REGION,YY,MMDD,RLD,SS = re.findall(regex_pattern,input_file).pop()
	#-- input file column types for ascii format LVIS files
	file_dtype = {}
	file_dtype['names']=('LVIS_LFID','Shot_Number','Time','Longitude_Centroid',
		'Latitude_Centroid','Elevation_Centroid','Longitude_Low','Latitude_Low',
		'Elevation_Low','Longitude_High','Latitude_High','Elevation_High')
	file_dtype['formats'] = ('i','i','f','f','f','f','f','f','f','f','f','f')
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
	year,month,day = np.array([YY,MMDD[:2],MMDD[2:]], dtype=np.float)
	JD = calc_julian_day(year,month,day)
	#-- converting to J2000 seconds and adding seconds since start of day
	LVIS_L2_input['J2000'] = (JD - 2451545.0)*86400.0 + LVIS_L2_input['Time']
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
