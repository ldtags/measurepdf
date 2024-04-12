from src._exceptions import (
    ETRMResponseError
)


class MeasureInfo:
    def __init__(self, res_json: object):
        try:
            self.name: str = res_json['name']
            self.url: str = res_json['url']
        except IndexError:
            raise ETRMResponseError


class MeasuresResponse:
    def __init__(self, res_json: object):
        try:
            self.count: int = res_json['count']
            self.next: str = res_json['next']
            self.previous: str = res_json['previous']
            self.results: list[MeasureInfo] = list(
                map(lambda res_measure: MeasureInfo(res_measure),
                    res_json['results']))
        except IndexError:
            raise ETRMResponseError


class MeasureVersionInfo:
    def __init__(self, res_json: object):
        try:
            self.version: str = res_json['version']
            self.status: str = res_json['status']
            self.change_description: str = res_json['change_description']
            self.owner: str = res_json['owner']
            self.is_published: bool = res_json['is_published']
            self.date_committed: str = res_json['date_committed']
            self.url: str = res_json['url']
        except IndexError:
            raise ETRMResponseError('malformed measure version info')


class MeasureVersionsResponse:
    def __init__(self, res_json: object):
        try:
            self.statewide_measure_id: str = res_json['statewide_measure_id']
            self.use_category: str = res_json['use_category']
            self.versions: list[MeasureVersionInfo] = list(
                map(lambda version: MeasureVersionInfo(version),
                    res_json['versions']))
        except IndexError:
            raise ETRMResponseError('malformed measure versions response')
