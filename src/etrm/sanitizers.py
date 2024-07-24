import re

from src import patterns
from src.etrm.exceptions import (
    UnauthorizedError,
    ETRMConnectionError,
    ETRMRequestError
)


def sanitize_auth_token(token: str) -> str:
    re_match = re.fullmatch(patterns.AUTH_TOKEN, token)
    if re_match is None:
        raise UnauthorizedError(f'invalid API key: {token}')

    token_type = 'Token'
    api_key = re_match.group(3)
    if not isinstance(api_key, str):
        raise ETRMConnectionError('An error occurred while parsing the '
                                  f' API key from {token}')

    sanitized = f'{token_type} {api_key}'
    return sanitized


def sanitize_statewide_id(statewide_id: str) -> str:
    re_match = re.search(patterns.STATEWIDE_WHITELIST, statewide_id)
    if re_match is not None:
        raise ETRMRequestError(f'Statewide ID [{statewide_id}] contains'
                               ' invalid characters')

    re_match = re.fullmatch(patterns.STWD_ID, statewide_id)
    if re_match is None:
        raise ETRMRequestError(f'Invalid statewide ID: {statewide_id}')

    stwd_id = re_match.group(1)
    if not isinstance(stwd_id, str):
        raise ETRMConnectionError('An error occurred while parsing the'
                                  f' statewide ID {statewide_id}')

    sanitized = stwd_id.upper()
    return sanitized


def sanitize_measure_id(measure_id: str) -> str:
    re_match = re.search(patterns.VERSION_WHITELIST, measure_id)
    if re_match is not None:
        raise ETRMRequestError(f'Measure version [{measure_id}] contains'
                               ' invalid characters')

    re_match = re.fullmatch(patterns.VERSION_ID, measure_id)
    if re_match is None:
        raise ETRMRequestError(f'Invalid measure version: {measure_id}')

    measure_version = re_match.group(1)
    if not isinstance(measure_version, str):
        raise ETRMConnectionError('An error occurred while parsing the'
                                  f' measure version {measure_id}')

    sanitized = measure_version.upper()
    return sanitized


def sanitize_reference(ref_id: str) -> str:
    re_match = re.search(patterns.REFERENCE_WHITELIST, ref_id)
    if re_match is not None:
        raise ETRMRequestError(f'Reference tag ID [{ref_id}] contains'
                               ' invalid characters')

    sanitized = ref_id.upper()
    return sanitized


def sanitize_table_name(table_name: str) -> str:
    re_match = re.search(patterns.TABLE_NAME_WHITELIST, table_name)
    if re_match is not None:
        raise ETRMRequestError(f'Table name [{table_name}] contains'
                               ' invalid characters')

    return table_name
