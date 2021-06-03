:orphan:


LeCroyDSO: LeCroy Communication Wrapper
=======================================

The LeCroyDSO package can be used to control LeCroy oscilloscopes
for instrument communications, setup, and data transfer.  All details 
of the interface bus used to connect to the Teledyne LeCroy instrument 
are encapsulated within the package.

A simple example, reading self-identification from a LeCroy oscilloscope
is a few lines of code::

    >>> from lecroydso import LeCroyDSO, LeCroyVISA
    >>> transport = LeCroyVISA('TCPIP0::127.0.0.1::inst0::INSTR')
    >>> dso = LeCroyDSO(transport)
    >>> print(dso.query('*IDN?'))
    LECROY,DDA804ZI,LCRY0401N22234,9.6.0
    >>>

This should work on Windows, Linux and Mac OS with the necessary backend
installed.

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
-------------

Using pip:

    $ pip install lecroydso

or download and unzip the source distribution file and:

    $ python setup.py install

Table of Contents
-----------------

.. toctree::
    :maxdepth: 2

    User guide <introduction/index.rst>
    FAQ <faq/index.rst>
    API Documentation <api/index.rst>
