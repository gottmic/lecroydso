"""LeCroy DSO communication utilities

.. moduleauthor:: Ashok Bruno <ashok.bruno@teledyne.com>

"""
# Copyright (c) 2018 Teledyne LeCroy, Inc.
# All rights reserved worldwide.
#
# This file is part of LeCroyDSO.
#
# LeCroyDSO is free software: You can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>

import sys

if sys.version_info >= (3, 8):
    from importlib.metadata import PackageNotFoundError, version
else:
    from importlib_metadata import PackageNotFoundError, version  # type: ignore

from lecroydso.dsoconnection import DSOConnection   # noqa
from lecroydso.errors import DSOConnectionError, DSOIOError, ParametersError    # noqa
from lecroydso.activedso import ActiveDSO       # noqa
from lecroydso.lecroyvisa import LeCroyVISA     # noqa
from lecroydso.lecroydso import LeCroyDSO       # noqa
from lecroydso.lecroyvicp import LeCroyVICP     # noqa

__version__ = "unknown"
try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass
