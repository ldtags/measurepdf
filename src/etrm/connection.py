import re
import requests
from typing import Self

from exceptions import UnauthorizedError
from etrm.models import (
    MeasuresResponse,
    MeasureVersionsResponse,
    Measure
)


def extract_id(_url: str) -> str | None:
    URL_RE = re.compile('https://www.caetrm.com/api/v1/measures/([a-zA-Z0-9]+)/')
    re_match = re.search(URL_RE, _url)
    if len(re_match.groups()) != 1:
        return None

    id_group = re_match.group(1)
    if not isinstance(id_group, str):
        return None

    return id_group


class ETRMConnection:
    api_url = 'https://www.caetrm.com/api/v1'

    def __init__(self, auth_token: str):
        self.auth_token = auth_token

    def close(self):
        del self.auth_token

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args):
        self.close()

    def get_measure(self, measure_id: str) -> Measure:
        statewide_id, version_id = measure_id.split('-', 1)
        headers = {
            'Authorization': self.auth_token
        }

        response = requests.get(f'{self.api_url}/measures/{statewide_id}/{version_id}',
                                headers=headers)

        if response.status_code != 200:
            raise UnauthorizedError()

        return Measure(response.json())

    def get_measure_ids(self,
                        offset: int = 0,
                        limit: int = 25
                       ) -> list[str]:
        params = {
            'offset': str(offset),
            'limit': str(limit)
        }

        headers = {
            'Authorization': self.auth_token
        }

        response = requests.get(f'{self.api_url}/measures',
                                params=params,
                                headers=headers)

        if response.status_code != 200:
            raise UnauthorizedError(f'invalid auth token: {self.auth_token}')

        response_body = MeasuresResponse(response.json())
        return list(map(lambda result: extract_id(result.url),
                        response_body.results))

    def get_measure_versions(self,
                             measure_id: str,
                             offset: int = 0,
                             limit: int = 25
                            ) -> list[str]:
        params = {
            'offset': str(offset),
            'limit': str(limit)
        }

        headers = {
            'Authorization': self.auth_token
        }

        response = requests.get(f'{self.api_url}/measures/{measure_id}/',
                                params=params,
                                headers=headers)

        if response.status_code != 200:
            raise UnauthorizedError()

        response_body = MeasureVersionsResponse(response.json())
        return sorted(list(map(lambda result: result.version,
                               response_body.versions)))
