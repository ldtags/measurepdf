import re
import requests
from typing import overload

from src import patterns
from src.etrm.models import (
    MeasuresResponse,
    MeasureVersionsResponse,
    Measure,
    Reference,
    SharedLookupRef,
    SharedValueTable
)
from src.exceptions import (
    ETRMResponseError,
    UnauthorizedError,
    NotFoundError,
    ETRMRequestError,
    ETRMConnectionError
)


API_URL = 'https://www.caetrm.com/api/v1'


def extract_id(_url: str) -> str | None:
    URL_RE = re.compile(f'{API_URL}/measures/([a-zA-Z0-9]+)/')
    re_match = re.search(URL_RE, _url)
    if len(re_match.groups()) != 1:
        return None

    id_group = re_match.group(1)
    if not isinstance(id_group, str):
        return None

    return id_group


class ETRMCache:
    """Cache for eTRM API response data

    Used to decrease eTRM API connection layer latency on repeat calls
    """

    def __init__(self):
        self.id_cache: list[str] = []
        self.__id_count: int = -1
        self.uc_id_caches: dict[str, list[str]] = {}
        self.__uc_id_counts: dict[str, int] = {}
        self.version_cache: dict[str, list[str]] = {}
        self.measure_cache: dict[str, Measure] = {}
        self.references: dict[str, Reference] = {}
        self.shared_value_tables: dict[str, SharedValueTable] = {}

    def get_ids(self,
                offset: int,
                limit: int,
                use_category: str | None=None
               ) -> tuple[list[str], int] | None:
        if use_category != None:
            try:
                id_cache = self.uc_id_caches[use_category]
                count = self.__uc_id_counts[use_category]
            except KeyError:
                return None
        else:
            id_cache = self.id_cache
            count = self.__id_count

        try:
            cached_ids = id_cache[offset:offset + limit]
            if len(cached_ids) == limit and all(cached_ids):
                return (cached_ids, count)
        except IndexError:
            return None
        return None

    def add_ids(self,
                measure_ids: list[str],
                offset: int,
                limit: int,
                count: int,
                use_category: str | None=None):
        if use_category != None:
            try:
                id_cache = self.uc_id_caches[use_category]
            except KeyError:
                self.uc_id_caches[use_category] = []
                id_cache = self.uc_id_caches[use_category]
            self.__uc_id_counts[use_category] = count
        else:
            id_cache = self.id_cache
            self.__id_count = count

        cache_len = len(id_cache)
        if offset == cache_len:
            id_cache.extend(measure_ids)
        elif offset > cache_len:
            id_cache.extend([''] * (offset - cache_len))
            id_cache.extend(measure_ids)
        elif offset + limit > cache_len:
            new_ids = measure_ids[cache_len - offset:limit]
            for i in range(offset, cache_len):
                if id_cache[i] == '':
                    id_cache[i] = measure_ids[i - offset]
            id_cache.extend(new_ids)

    def get_versions(self, measure_id: str) -> list[str] | None:
        return self.version_cache.get(measure_id, None)

    def add_versions(self, measure_id: str, versions: list[str]):
        self.version_cache[measure_id] = versions

    def get_measure(self, version_id: str) -> Measure | None:
        return self.measure_cache.get(version_id, None)

    def add_measure(self, measure: Measure):
        self.measure_cache[measure.full_version_id] = measure

    def get_reference(self, ref_id: str) -> Reference | None:
        return self.references.get(ref_id, None)

    def add_reference(self, ref_id: str, reference: Reference):
        self.references[ref_id] = reference

    def get_shared_value_table(self,
                               table_name: str,
                               version: str
                              ) -> SharedValueTable | None:
        return self.shared_value_tables.get(f'{table_name}-{version}', None)

    def add_shared_value_table(self,
                               table_name: str,
                               version: str,
                               value_table: SharedValueTable):
        self.shared_value_tables[f'{table_name}-{version}'] = value_table


class ETRMConnection:
    """eTRM API connection layer"""

    def __init__(self, auth_token: str):
        self.auth_token = self.__sanitize_auth_token(auth_token)
        self.headers = {
            'Authorization': auth_token
        }
        self.cache = ETRMCache()

    def __sanitize_auth_token(self, token: str) -> str:
        re_match = re.fullmatch(patterns.AUTH_TOKEN, token)
        if re_match == None:
            raise UnauthorizedError(f'invalid API key: {token}')

        token_type = 'Token'
        api_key = re_match.group(3)
        if not isinstance(api_key, str):
            raise ETRMConnectionError('An error occurred while parsing the '
                                      f' API key from {token}')

        return f'{token_type} {api_key}'

    def get(self,
            url: str,
            headers: dict[str, str] | None=None,
            params: dict[str, str] | None=None,
            stream: bool=True,
            **kwargs
           ) -> requests.Response:
        req_headers: dict[str, str] = {**self.headers}
        if headers != None:
            req_headers |= headers

        try:
            response = requests.get(url,
                                    params=params,
                                    headers=req_headers,
                                    stream=stream,
                                    **kwargs)
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError() from err

        match response.status_code:
            case 200:
                return response
            case 401:
                raise UnauthorizedError('Unauthorized API key:'
                                        f' {self.auth_token}')
            case 404:
                raise NotFoundError(f'No resource found at [{url}]')
            case 500:
                raise ETRMResponseError('Server error occurred while'
                                        ' attempting to access the resource'
                                        f' at [{url}]')
            case status:
                raise ETRMResponseError('Unexpected status code received:'
                                        f' {status}')

    def get_measure(self, full_version_id: str) -> Measure:
        cached_measure = self.cache.get_measure(full_version_id)
        if cached_measure != None:
            return cached_measure

        statewide_id, version_id = full_version_id.split('-', 1)
        url = f'{API_URL}/measures/{statewide_id}/{version_id}'
        response = self.get(url)
        measure = Measure(response.json())
        self.cache.add_measure(measure)
        return measure

    def get_measure_ids(self,
                        offset: int=0,
                        limit: int=25,
                        use_category: str | None=None
                       ) -> tuple[list[str], int]:
        cache_response = self.cache.get_ids(offset, limit, use_category)
        if cache_response != None:
            return cache_response

        params = {
            'offset': str(offset),
            'limit': str(limit)
        }

        if use_category != None:
            params['use_category'] = use_category

        response = self.get(f'{API_URL}/measures', params=params)
        response_body = MeasuresResponse(response.json())
        measure_ids = list(map(lambda result: extract_id(result.url),
                               response_body.results))
        count = response_body.count
        self.cache.add_ids(measure_ids=measure_ids,
                           offset=offset,
                           limit=limit,
                           count=count,
                           use_category=use_category)
        return (measure_ids, count)

    def get_all_measure_ids(self, use_category: str | None=None) -> list[str]:
        _, count = self.get_measure_ids(use_category=use_category)
        measure_ids, _ = self.get_measure_ids(offset=0,
                                              limit=count,
                                              use_category=use_category)
        return measure_ids

    def get_measure_versions(self, measure_id: str) -> list[str]:
        cached_versions = self.cache.get_versions(measure_id)
        if cached_versions != None:
            return list(reversed(cached_versions))

        response = self.get(f'{API_URL}/measures/{measure_id}/')
        response_body = MeasureVersionsResponse(response.json())
        measure_versions = sorted(map(lambda result: result.version,
                                      response_body.versions))
        self.cache.add_versions(measure_id, measure_versions)
        return list(reversed(measure_versions))

    def get_reference(self, ref_id: str) -> Reference:
        cached_ref = self.cache.get_reference(ref_id)
        if cached_ref is not None:
            return cached_ref

        response = self.get(f'{API_URL}/references/{ref_id}/')
        reference = Reference(response.json())
        self.cache.add_reference(ref_id, reference)
        return reference

    @overload
    def get_shared_value_table(self,
                               lookup_ref: SharedLookupRef
                              ) -> SharedValueTable:
        ...

    @overload
    def get_shared_value_table(self,
                               table_name: str,
                               version: str | int
                              ) -> SharedValueTable:
        ...

    def get_shared_value_table(self, *args) -> SharedValueTable:
        if len(args) == 1:
            if not isinstance(args[0], SharedLookupRef):
                raise ETRMRequestError(f'unknown overload args: {args}')
            table_name = args[0].name
            version = args[0].version
            url = args[0].url
        elif len(args) == 2:
            if not (isinstance(args[0], str)
                        and isinstance(args[1], str | int)):
                raise ETRMRequestError(f'unknown overload args: {args}')
            table_name = args[0]
            version = f'{args[1]:03d}'
            url = f'{API_URL}/shared-value-tables/{table_name}/{version}'
        else:
            raise ETRMRequestError('missing required parameters')

        cached_table = self.cache.get_shared_value_table(table_name, version)
        if cached_table is not None:
            return cached_table

        response = self.get(url)
        value_table = SharedValueTable(response.json())
        self.cache.add_shared_value_table(table_name, version, value_table)
        return value_table
