import os
from setuptools import setup, find_packages

# package description and keywords
description = ('Python tools for reading Operation IceBridge LVIS and '
    'LVIS Global Hawk Level-2 data products')
keywords = ('Operation IceBridge, ILVIS2, ILVGH2, laser altimetry, '
    'surface elevation and change')
# get long_description from README.rst
with open("README.md", "r") as fh:
    long_description = fh.read()
long_description_content_type = "text/markdown"

# get install requirements
with open('requirements.txt') as fh:
    install_requires = [line.split().pop(0) for line in fh.read().splitlines()]

# get version
with open('version.txt') as fh:
    version = fh.read()

# list of all scripts to be included with package
scripts=[os.path.join('scripts',f) for f in os.listdir('scripts') if f.endswith('.py')]

setup(
    name='read-LVIS2-elevation',
    version=version,
    description=description,
    long_description=long_description,
    long_description_content_type=long_description_content_type,
    url='https://github.com/tsutterley/read-LVIS2-elevation',
    author='Tyler Sutterley',
    author_email='tsutterl@uw.edu',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords=keywords,
    packages=find_packages(),
    install_requires=install_requires,
    scripts=scripts,
)
