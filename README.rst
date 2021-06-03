LeCroyDSO
=========

A Python package for communicating to LeCroy oscilloscopes via various 
protocols VICP, VXI, USBTMC or GPIB.

Description
-----------

This package can use ActiveDSO or LeCroyVISA as the wrapper for communication.
ActiveDSO will only work on Windows and uses an ActiveX DLL to communicate to the DSO. 
LeCroyVISA uses the python package pyvisa to communicate. Please see the pyvisa documentation
for additional information.

Requirements
------------

- Python (tested with 3.6+)
- VISA (tested with NI-VISA 19.5, Win10, from www.ni.com/visa and Keysight-VISA )

Installation
--------------

Using pip:

    $ pip install lecroydso

or download and unzip the source distribution file and:

    $ python setup.py install


Documentation
--------------

The documentation can be read online at https://lecroydso.readthedocs.org

