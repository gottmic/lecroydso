.. _intro-getting:

Installation
============

.. include:: ../substitutions.sub

LeCroyDSO is a communication layer to LeCroy Oscilloscopes. It runs on Python 3.6+.

You can install it using pip_::

    $ pip install -U lecroydso


Backend
-------

In order for LeCroyDSO to work, you need to have a suitable backend. PyVISA
includes a backend that wraps the `National Instruments's VISA`_ library.
However, you need to download and install the library yourself
(See :ref:`faq-getting-nivisa`). There are multiple VISA implementations from
different vendors. PyVISA is tested against `National Instruments's VISA`_ and
`Keysight IO Library Suite`_ which can both be downloaded for free (you do not
need a development environment only the driver library).

.. warning::

    LeCroyDSO works with 32- and 64- bit Python and can deal with 32- and 64-bit
    VISA libraries without any extra configuration. What PyVISA cannot do is
    open a 32-bit VISA library while running in 64-bit Python (or the other
    way around).

**You need to make sure that the Python and VISA library have the same bitness**

Testing your installation
-------------------------


That's all! You can check that LeCroyDSO is correctly installed by starting up
python, and creating a connection:

    >>> from activedso import ActiveDSO
    >>> rm = lecroydso.ResourceManager()
    >>> print(rm.list_resources())

If you encounter any problem, take a look at the :ref:`faq-faq`. There you will
find the solutions to common problem as well as useful debugging techniques.
If everything fails, feel free to open an issue in our `issue tracker`_


Using the development version
-----------------------------

You can install the latest development version (at your own risk) directly
form GitHub_::

    $ pip install -U git+https://github.com/lecroydso/lecroydso.git


.. _easy_install: http://pypi.python.org/pypi/setuptools
.. _Python: http://www.python.org/
.. _pip: http://www.pip-installer.org/
.. _`Anaconda`: https://www.anaconda.com/distribution/
.. _PyPI: https://pypi.python.org/pypi/PyVISA
.. _GitHub: https://github.com/lecroydso/lecroydso
.. _`National Instruments's VISA`: https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html
.. _`Keysight IO Library SUite`: https://www.keysight.com/en/pd-1985909/io-libraries-suite/
.. _`issue tracker`: https://github.com/lecroydso/lecroydso/issues
.. _`PyVISA-Py`: http://lecroydso-py.readthedocs.io/en/latest/
