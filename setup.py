from setuptools import setup, find_packages
setup(
	name='read-LVIS2-elevation',
	version='1.0.0.2',
	description='Reads Operation IceBridge LVIS and LVIS Global Hawk Level-2 data products',
	url='https://github.com/tsutterley/read-LVIS2-elevation',
	author='Tyler Sutterley',
	author_email='tyler.c.sutterley@nasa.gov',
	license='MIT',
	classifiers=[
		'Development Status :: 3 - Alpha',
		'Intended Audience :: Science/Research',
		'Topic :: Scientific/Engineering :: Physics',
		'License :: OSI Approved :: MIT License',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
	],
	keywords='NSIDC IceBridge ILVIS2 ILVGH2',
	packages=find_packages(),
	install_requires=['numpy','h5py','lxml','future'],
)
