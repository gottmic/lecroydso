.. _faq-contributing:

Contributing to LeCroyDSO
======================

You can contribute in different ways:

Report issues
-------------

You can report any issues with the package, the documentation to the LeCroyDSO
`issue tracker`_. Also feel free to submit feature requests, comments or
questions. In some cases, platform specific information is required. If you
think this is the case, run the following command and paste the output into
the issue::

    pyvisa-info

It is useful that you also provide the log output. To obtain it, add the
following lines to your code::

    import pyvisa
    pyvisa.log_to_screen()

If your issue concern a specific instrument please be sure to indicate the
manufacturer and the model.


Contribute code
---------------

To contribute fixes, code or documentation to LeCroyDSO, send us a patch, or fork
LeCroyDSO in github_ and submit the changes using a pull request.

You can also get the code from PyPI_ or GitHub_. You can clone the
public repository::

    $ git clone git://github.com/pyvisa/pyvisa.git

Once you have a copy of the source, you can embed it in your Python package,
or install it in develop mode easily::

    $ python setup.py develop

Installing in development mode means that any change you make will be immediately
reflected when you run pyvisa.

LeCroyDSO uses a number of tools to ensure a consistent code style and quality. The
code is checked as part of the CIs system but you may want to run those locally before
submitting a patch. You have multiple options to do so:

- You can install `pre-commit` (using pip for example) and run::

      $pre-commit install

This will run all the above mentioned tools run when you commit your changes.

- Install and run each tool independently. You can install all of them using pip
  and the `dev_requirements.txt` file. You can a look at the CIs configurations
  (in .github/workflows/ci.yml). Thoses tools are:

    - black: Code formatting
    - isort: Import sorting
    - flake8: Code quality
    - mypy: Typing

Finally if editing docstring, please note that LeCroyDSO uses Numpy style docstring.
In order to build the documentation you will need to install `sphinx` and
`sphinx_rtd_theme`. Both are listed in `dev_requirements.txt`.



.. _easy_install: http://pypi.python.org/pypi/setuptools
.. _Python: http://www.python.org/
.. _pip: http://www.pip-installer.org/
.. _`Anaconda`: https://www.anaconda.com/distribution/
.. _PyPI: https://pypi.python.org/pypi/LeCroyDSO
.. _`National Instruments's VISA`: http://ni.com/visa/
.. _github: http://github.com/pyvisa/pyvisa
.. _`issue tracker`: https://github.com/pyvisa/pyvisa/issues
