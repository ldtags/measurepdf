"""Compiled general use RegEx patterns"""


import re


__UC_ID = r'^SW([A-Za-z]{2})$'
UC_ID = re.compile(__UC_ID)
"""Statewide Use Category ID RegEx Pattern

Group 1: Use Category
"""


__STWD_ID = r'^[A-Za-z]{3,}[0-9]{2,}$'
STWD_ID = re.compile(__STWD_ID)


__VRSN_ID = r'^(([A-Za-z]{3,}[0-9]{2,})-([0-9]+(?:-.+)?))$'
VRSN_ID = re.compile(__VRSN_ID)
