import re
import requests

from src.etrm.models import (
    MeasuresResponse,
    MeasureVersionsResponse,
    Measure,
    Reference
)
from src.exceptions import (
    ETRMResponseError,
    UnauthorizedError,
    NotFoundError
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
    """Cache for eTRM API response data.

    Decreases time required for repeat API calls for the same data.
    """

    def __init__(self):
        self.id_cache: list[str] = []
        self.__id_count: int = -1
        self.uc_id_caches: dict[str, list[str]] = {}
        self.__uc_id_counts: dict[str, int] = {}
        self.version_cache: dict[str, list[str]] = {}
        self.measure_cache: dict[str, Measure] = {}

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
            if cached_ids != [] and all(cached_ids):
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


class ETRMConnection:
    """eTRM API connection layer."""

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.cache = ETRMCache()

    def get_measure(self, full_version_id: str) -> Measure:
        """Returns a detailed measure object.

        Errors:
            `NotFoundError` - (404) measure not found

            `ETRMResponseError` - (500) server error

            `UnauthorizedError` - (!200) any other error
        """

        cached_measure = self.cache.get_measure(full_version_id)
        if cached_measure != None:
            return cached_measure

        statewide_id, version_id = full_version_id.split('-', 1)
        headers = {
            'Authorization': self.auth_token
        }

        url = f'{API_URL}/measures/{statewide_id}/{version_id}'
        try:
            response = requests.get(url,
                                    headers=headers,
                                    stream=True)
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError from err

        if response.status_code == 404:
            raise NotFoundError(f'Measure {full_version_id} could not be'
                                ' found')

        if response.status_code == 500:
            raise ETRMResponseError('Server error occurred when retrieving'
                                    f' measure {full_version_id}')

        if response.status_code != 200:
            raise UnauthorizedError(f'Unauthorized token: {self.auth_token}')

        measure = Measure(response.json())
        self.cache.add_measure(measure)
        return measure

    def get_measure_ids(self,
                        offset: int=0,
                        limit: int=25,
                        use_category: str | None=None
                       ) -> tuple[list[str], int]:
        """Returns a list of measure ids.

        Errors:
            `NotFoundError` - (404) measure not found

            `ETRMResponseError` - (500) server error

            `UnauthorizedError` - (!200) any other error
        """

        cache_response = self.cache.get_ids(offset, limit, use_category)
        if cache_response != None:
            return cache_response

        params = {
            'offset': str(offset),
            'limit': str(limit)
        }

        if use_category != None:
            params['use_category'] = use_category

        headers = {
            'Authorization': self.auth_token
        }

        try:
            response = requests.get(f'{API_URL}/measures',
                                    params=params,
                                    headers=headers)
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError from err

        if response.status_code == 404:
            raise NotFoundError(f'Measures could not be found')

        if response.status_code == 500:
            raise ETRMResponseError('Server error occurred when retrieving'
                                    ' measures')

        if response.status_code != 200:
            raise UnauthorizedError(f'Unauthorized token: {self.auth_token}')

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
        """Returns a list of versions of the measure with the ID
        `measure_id`.

        Errors:
            `NotFoundError` - (404) measure not found

            `ETRMResponseError` - (500) server error

            `UnauthorizedError` - (!200) any other error
        """

        cached_versions = self.cache.get_versions(measure_id)
        if cached_versions != None:
            return list(reversed(cached_versions))

        headers = {
            'Authorization': self.auth_token
        }

        url = f'{API_URL}/measures/{measure_id}/'
        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError from err

        if response.status_code == 404:
            raise NotFoundError(f'No versions for measure {measure_id}'
                                ' were found')

        if response.status_code == 500:
            raise ETRMResponseError('Server error occurred while retrieving'
                                    f' versions for measure {measure_id}')

        if response.status_code != 200:
            raise UnauthorizedError(f'Unauthorized token: {self.auth_token}')

        response_body = MeasureVersionsResponse(response.json())
        measure_versions = sorted(map(lambda result: result.version,
                                      response_body.versions))
        self.cache.add_versions(measure_id, measure_versions)
        return list(reversed(measure_versions))

    def get_reference(self, reference: str) -> Reference:
        """Returns the reference associated with `reference`

        Errors:
            `NotFoundError` - (404) reference not found

            `ETRMResponseError` - (500) server error

            `UnauthorizedError` - (!200) any other error
        """

        headers = {
            'Authorization': self.auth_token
        }

        url = f'{API_URL}/references/{reference}/'
        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError from err

        if response.status_code == 404:
            raise NotFoundError(f'No reference with the id {reference}'
                                ' was found')

        if response.status_code == 500:
            raise ETRMResponseError('Server error occurred while retrieving'
                                    f' reference {reference}')

        if response.status_code != 200:
            raise UnauthorizedError(f'Unauthorized token: {self.auth_token}')

        return Reference(response.json())
