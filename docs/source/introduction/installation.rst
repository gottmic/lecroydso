.. _intro-installation:

Installation
============

.. include:: ../substitutions.sub

LeCroyDSO is a communication layer to LeCroy Oscilloscopes. It runs on Python 3.6+.

You can install it using pip_::

    $ pip install -U lecroydso

Backend
-------

In order for LeCroyDSO to work, you need to have a suitable DSOConnection. 
LeCroyDSO is tested against `National Instruments's VISA`_ and
`Keysight IO Library Suite`_ which can both be downloaded for free (you do not
need a development environment only the driver library).

.. warning::

    LeCroyDSO works with 32- and 64- bit Python and can deal with 32- and 64-bit
    VISA libraries without any extra configuration. What LeCroyDSO cannot do is
    open a 32-bit VISA library while running in 64-bit Python (or the other
    way around).

**You need to make sure that the Python and VISA library have the same bitness**

Using the development version
-----------------------------

You can install the latest development version (at your own risk) directly
from GitHub_::

    $ pip install -U git+https://github.com/lecroydso/lecroydso.git

.. _`PyVISA`: http://pyvisa.readthedocs.io/en/latest/
.. _easy_install: http://pypi.python.org/pypi/setuptools
.. _Python: http://www.python.org/
.. _pip: http://www.pip-installer.org/
.. _`Anaconda`: https://www.anaconda.com/distribution/
.. _PyPI: https://pypi.python.org/pypi/PyVISA
.. _GitHub: https://github.com/lecroydso/lecroydso
.. _`National Instruments's VISA`: https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html
.. _`Keysight IO Library Suite`: https://www.keysight.com/en/pd-1985909/io-libraries-suite/
.. _`issue tracker`: https://github.com/lecroydso/lecroydso/issues
