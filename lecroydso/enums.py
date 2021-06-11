# -----------------------------------------------------------------------------
# Summary:		Implementation of ActiveDSO class
# Authors:		Ashok Bruno
# Started:		4/27/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
# -----------------------------------------------------------------------------
#

import enum


class TriggerMode(str, enum):
    AUTO = 'AUTO'
    NORMAL = 'NORMAL'
    SINGLE = 'SINGLE'
    STOPPED = 'STOPPED'
