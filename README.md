read-LVIS2-elevation
====================

#### Reads Operation IceBridge LVIS and LVIS Global Hawk Level-2 data products

- [IceBridge LVIS Level-2 Geolocated Surface Elevation Product](http://nsidc.org/data/ilvis2/)  
- [IceBridge LVIS-GH Level-2 Geolocated Surface Elevation Product](http://nsidc.org/data/ilvgh2/)  
- [Operation IceBridge LVIS Data Structure](https://lvis.gsfc.nasa.gov/Data/DataStructure.html)  
- [NSIDC IceBridge Software Tools](http://nsidc.org/data/icebridge/tools.html)
- [Python program for retrieving Operation IceBridge data](https://github.com/tsutterley/nsidc-earthdata)

#### Calling Sequence
```
from read_LVIS2_elevation import read_LVIS2_elevation
LVIS_L2_input = read_LVIS2_elevation('example_filename.TXT')
```

#### `nsidc_convert_ILVIS2.py`
Alternative program to read IceBridge Geolocated LVIS Elevation Product files directly from NSIDC server as bytes and output as HDF5 files  

#### Dependencies
- [numpy: Scientific Computing Tools For Python](http://www.numpy.org)
- [h5py: Python interface for Hierarchal Data Format 5 (HDF5)](http://h5py.org)  
- [lxml: processing XML and HTML in Python](https://pypi.python.org/pypi/lxml)
- [future: Compatibility layer between Python 2 and Python 3](http://python-future.org/)  

#### Download
The program homepage is:   
https://github.com/tsutterley/read-LVIS2-elevation   
A zip archive of the latest version is available directly at:    
https://github.com/tsutterley/read-LVIS2-elevation/archive/master.zip  

#### Disclaimer  
This program is not sponsored or maintained by the Universities Space Research Association (USRA), the National Snow and Ice Data Center (NSIDC) or NASA.  It is provided here for your convenience but _with no guarantees whatsoever_.  
