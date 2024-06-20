import re


_STWD_ID = r'^(([A-Za-z]{2})([A-Za-z]{2})([0-9]{2,}))$'
STWD_ID = re.compile(_STWD_ID)
"""eTRM Measure Statewide ID Pattern

Group 1: Statewide ID
Group 2: Measure Type
Group 3: Use Category
Group 4: Use Category Version
"""


_VRSN_ID = r'^(([A-Za-z]{4}[0-9]{2,})-([0-9]+(?:-.+)?))$'
VRSN_ID = re.compile(_VRSN_ID)
"""eTRM Measure Version ID Pattern

Group 1: Full Version ID\n
Group 2: Statewide ID\n
Group 3: Version ID (including optional draft version)
"""
