import re

from src import patterns, lookups
from src.app.types import _ID_FILTER, _VERSION_FILTER


class HomeModel:
    """MVC model for the Home module."""

    def __init__(self):
        self.__count: int = 0
        self.__offset: int = 0
        self.__limit: int = 25
        self.__use_category: str | None = None
        self.__measure_ids: list[str] = []
        self.__measure_versions: dict[str, list[str]] = {}
        self.selected_measures: list[str] = []
        self.selected_versions: list[str] = []

    @property
    def count(self) -> int:
        return self.__count

    @count.setter
    def count(self, new_count: int) -> None:
        if new_count < 0:
            raise ValueError(f'Invalid Count: count value {new_count}'
                             ' must be a non-negative integer')

        self.__count = new_count

    @property
    def offset(self) -> int:
        return self.__offset

    @offset.setter
    def offset(self, new_offset: int) -> None:
        if new_offset < 0:
            raise ValueError(f'Invalid Offset: offset value {new_offset}'
                             ' must be a non-negative integer')

        if new_offset > self.count:
            raise ValueError(f'Invalid Offset: offset value {new_offset}'
                             f' must be less than the count {self.count}')

        self.__offset = new_offset

    @property
    def limit(self) -> int:
        return self.__limit

    @limit.setter
    def limit(self, new_limit: int) -> None:
        if new_limit < 0:
            raise ValueError(f'Invalid Limit: limit value {new_limit}'
                             ' must be a non-negative integer')

        if new_limit > self.count:
            raise ValueError(f'Invalid Limit: limit value {new_limit}'
                             f' must be less than the count {self.count}')

    @property
    def use_category(self) -> str | None:
        return self.__use_category

    @use_category.setter
    def use_category(self, new_uc: str | None) -> None:
        if new_uc is None:
            self.__use_category = new_uc
            return

        try:
            lookups.USE_CATEGORIES[new_uc]
        except KeyError:
            keys = list(lookups.USE_CATEGORIES.keys())
            raise ValueError(f'Invalid Use Category: use category {new_uc}'
                             ' is not a recognized use category.'
                             f'\nValid use categories are: {keys}')

        self.__use_category = new_uc

    @property
    def measure_ids(self) -> list[str]:
        return self.__measure_ids

    @measure_ids.setter
    def measure_ids(self, ids: list[str]) -> None:
        for measure_id in ids:
            re_match = re.fullmatch(patterns.STWD_ID, measure_id)
            if re_match is None:
                raise RuntimeError(f'Invalid Statewide ID: {measure_id}')

        self.__measure_ids = ids

    @property
    def measure_versions(self) -> dict[str, list[str]]:
        return self.__measure_versions

    @measure_versions.setter
    def measure_versions(self, versions: dict[str, list[str]]):
        for version in versions:
            re_match = re.fullmatch(patterns.VERSION_ID, version)
            if re_match is None:
                raise RuntimeError(f'Invalid Version: {version}')

        self.__measure_versions = versions

    @property
    def all_versions(self) -> list[str]:
        _all_versions: list[str] = []
        for _, versions in self.measure_versions.items():
            _all_versions.extend(versions)
        return _all_versions

    @all_versions.setter
    def all_versions(self, versions: list[str]) -> None:
        measure_versions: dict[str, list[str]] = {}
        for version in versions:
            re_match = re.search(patterns.VERSION_ID, version)
            if re_match is None:
                raise RuntimeError(f'Invalid Version: {version}')

            statewide_id = str(re_match.group(2))
            try:
                measure_versions[statewide_id].append(version)
            except KeyError:
                measure_versions[statewide_id] = [version]
        self.measure_versions = measure_versions

    def get_measure_versions(self, statewide_id: str | None=None) -> list[str]:
        if statewide_id is None:
            return self.all_versions
        return self.__measure_versions.get(statewide_id, [])

    def set_measure_versions(self, versions: list[str]) -> None:
        self.all_versions = versions

    def filter_versions(self,
                        statewide_id: str | None=None,
                        version: str | None=None
                       ) -> None:
        measure_versions = self.__measure_versions
        id_filters: list[_ID_FILTER] = [
            lambda entry: (
                statewide_id is None or entry[0] == statewide_id
            )
        ]
        measure_versions = dict(
            filter(
                lambda entry: (
                    all([id_filter(entry) for id_filter in id_filters])
                ),
                measure_versions.items()
            )
        )

        version_filters: list[_VERSION_FILTER] = [
            lambda version_id: (
                version is None or (
                    lambda re_match: (
                        isinstance(re_match, re.Match)
                            and re_match.group(6) == version
                    )
                    (re.search(patterns.VERSION_ID, version_id))
                )
            )
        ]
        for _statewide_id, versions in measure_versions.items():
            measure_versions[_statewide_id] = list(
                filter(
                    lambda version_id: (
                        all([_filter(version_id)
                                for _filter
                                in version_filters])
                    ),
                    versions
                )
            )
        self.__measure_versions = measure_versions

    def increment_offset(self) -> None:
        try:
            self.offset += self.limit
        except ValueError:
            self.offset = self.count - self.limit

    def decrement_offset(self) -> None:
        try:
            self.offset -= self.limit
        except ValueError:
            self.offset = 0
