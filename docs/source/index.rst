:orphan:


LeCroyDSO: LeCroy communication wrapper
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
    >>> print(dso.send_query('*IDN?'))
    LECROY,DDA804ZI,CHE-LABRUNO,0.8.6
    >>>

This should work on Windows, Linux and Mac OS with the necessary backend
installed.


.. toctree::
    :maxdepth: 2

    User guide <introduction/index.rst>
    FAQ <faq/index.rst>
    API Documentation <api/index.rst>
