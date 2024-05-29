import re


__STWD_ID = r'^[A-Za-z]{3,}[0-9]{2,}$'
STWD_ID = re.compile(__STWD_ID)


__VRSN_ID = r'^(([A-Za-z]{3,}[0-9]{2,})-([0-9]+(?:-.+)?))$'
VRSN_ID = re.compile(__VRSN_ID)
