import re
import requests

from src.etrm.models import (
    MeasuresResponse,
    MeasureVersionsResponse,
    Measure
)
from src.exceptions import UnauthorizedError


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


class ETRMConnection:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token

    def get_measure(self, measure_id: str) -> Measure:
        statewide_id, version_id = measure_id.split('-', 1)
        headers = {
            'Authorization': self.auth_token
        }

        url = f'{API_URL}/measures/{statewide_id}/{version_id}'
        response = requests.get(url,
                                headers=headers,
                                stream=True)

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

        response = requests.get(f'{API_URL}/measures',
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

        response = requests.get(f'{API_URL}/measures/{measure_id}/',
                                params=params,
                                headers=headers)

        if response.status_code != 200:
            raise UnauthorizedError()

        response_body = MeasureVersionsResponse(response.json())
        return sorted(list(map(lambda result: result.version,
                               response_body.versions)))
