"""Compiled general use RegEx patterns"""


import re


__AUTH_TOKEN = r'^(([Tt]oken )?([a-fA-F0-9]+))$'
AUTH_TOKEN = re.compile(__AUTH_TOKEN)
"""eTRM API Key RegEx Pattern

Group 1: eTRM API Key (including token type)\n
Group 2: Token Type\n
Group 3: eTRM API Key (excluding token type)
"""


__UC = r'^((?:SW)?([A-Za-z]{2}))$'
USE_CATEGORY = re.compile(__UC)
"""Statewide Use Category ID RegEx Pattern

Group 1: Statewide ID\n
Group 2: Use Category
"""


__STWD_ID = r'(([A-Za-z]{2})([A-Za-z]{2})([0-9]{2,}))'
STWD_ID = re.compile(rf'^{__STWD_ID}$')
"""eTRM Measure Statewide ID RegEx Pattern

Group 1: Statewide ID\n
Group 2: Measure Type\n
Group 3: Use Category\n
Group 4: Use Category Version
"""


__VRSN_ID = rf'({__STWD_ID}-([0-9]+(?:-.+)?))'
VERSION_ID = re.compile(rf'^{__VRSN_ID}$')
"""eTRM Measure Version ID RegEx Pattern

Group 1: Full Version ID\n
Group 2: Statewide ID\n
Group 3: Measure Type\n
Group 4: Use Category\n
Group 5: Use Category Version\n
Group 6: Measure Version Number (including optional draft version)
"""


__STWD_WHITELIST = r'[^A-Za-z0-9]'
STATEWIDE_WHITELIST = re.compile(__STWD_WHITELIST)
"""eTRM Connection Measure Statewide ID Whitelist RegEx Pattern

Use to sanitize prepared eTRM API requests that accept a statewide ID.

If a match is found, the string contains invalid characters.
"""


__VRSN_WHITELIST = r'[^A-Za-z0-9\-]'
VERSION_WHITELIST = re.compile(__VRSN_WHITELIST)
"""eTRM Connection Measure Version Whitelist RegEx Pattern

Use to sanitize prepared eTRM API requests that accept a measure ID.

If a match is found, the string contains invalid characters.
"""


__REF_WHITELIST = r'[^rR0-9]'
REFERENCE_WHITELIST = re.compile(__REF_WHITELIST)
"""eTRM Connection Reference Whitelist RegEx Pattern

Use to sanitize prepared eTRM API requests that accept a reference tag ID.

If a match is found, the string contains invalid characters.
"""


__TBL_NAME_WHITELIST = r'[^A-Za-z0-9]'
TABLE_NAME_WHITELIST = re.compile(__TBL_NAME_WHITELIST)
"""eTRM Connection Value Table Name Whitelist RegEx Pattern

Use to sanitize prepared eTRM API requests that accept a value table name.

If a match is found, the string contains invalid characters.
"""


__DATE = (
    '('
        r'([0-9]{4})'
        '-'
        r'((?:1[0-2])|(?:0?[1-9]))'
        '-'
        r'((?:0?[1-9])|(?:[1-2][0-9])|(?:[3][0-1]))'
    ')'
)
DATE = re.compile(rf'^{__DATE}$')
"""eTRM Date Representation RegEx Pattern

Group 1: Year\n
Group 2: Month\n
Group 3: Day
"""
