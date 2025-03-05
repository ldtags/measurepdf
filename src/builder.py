import os
import re
import time
import logging
import datetime as dt

from src import lookups, resources, patterns, utils, _ROOT
from src.etrm import ETRMConnection, Measure
from src.summarygen import MeasureSummary


logger = logging.getLogger(__name__)


class MeasureFilter:
    def __init__(
        self,
        use_categories: list[str] | None = None,
        min_start_date: dt.datetime | None = None,
        max_start_date: dt.datetime | None = None,
        min_end_date: dt.datetime | None = None,
        max_end_date: dt.datetime | None = None
    ) -> None:
        if use_categories is not None:
            self.use_categories = set(use_categories)
        else:
            self.use_categories = None

        self.min_start_date = min_start_date
        self.max_start_date = max_start_date
        self.min_end_date = min_end_date
        self.max_end_date = max_end_date

    def is_allowed_measure_id(self, measure_id: str) -> bool:
        re_match = re.fullmatch(patterns.STWD_ID, measure_id)
        if re_match is None:
            return False

        try:
            use_category = str(re_match.group(3))
        except ValueError:
            return False

        if self.use_categories is not None and use_category not in self.use_categories:
            return False

        return True

    def is_allowed_measure(self, measure: Measure) -> bool:
        if self.use_categories is not None and measure.use_category not in self.use_categories:
            return False

        if self.min_start_date is not None and measure.start_date < self.min_start_date:
            return False

        if self.max_start_date is not None and measure.start_date >= self.max_start_date:
            return False

        if (self.min_end_date is not None
                and measure.end_date is not None
                and measure.end_date < self.min_end_date):
            return False

        if (self.max_end_date is not None
                and measure.end_date is not None
                and measure.end_date >= self.max_end_date):
            return False

        return True

    def filter_measures(self, measures: list[Measure]) -> list[Measure]:
        return list(
            filter(
                lambda measure: self.is_allowed_measure(measure),
                measures
            )
        )


class Builder:
    def __init__(self, api_key: str | None = None):
        _api_key = api_key or resources.get_api_key(role="user")
        self.connection = ETRMConnection(_api_key, use_persistent_cache=True)

    def _get_measures(
        self,
        version_ids: list[str],
        _filter: MeasureFilter | None = None,
        limit: int | None = None        
    ) -> list[Measure]:
        measures: list[Measure] = []
        _filter = _filter or MeasureFilter()
        version_ids.sort(key=utils.version_key)
        for version_id in version_ids:
            measure = self.connection.get_measure(version_id)
            if not _filter.is_allowed_measure(measure):
                continue

            measures.append(measure)
            if limit is not None and len(measures) >= limit:
                break

        return measures

    def get_measures(
        self,
        _filter: MeasureFilter,
        measure_versions: list[str] | None = None,
        limit: int | None = None
    ) -> list[Measure]:
        logger.info("Adding measures...")
        logger.info(f"\tMeasure Versions: {measure_versions}")
        logger.info(f"\tUse Categories  : {_filter.use_categories}")
        logger.info(f"\tMin Start Date  : {_filter.min_start_date}")
        logger.info(f"\tMax Start Date  : {_filter.max_start_date}")
        logger.info(f"\tMin End Date    : {_filter.min_end_date}")
        logger.info(f"\tMax End Date    : {_filter.max_end_date}")
        logger.info(f"\tLimit           : {limit}")

        measures: list[Measure] = []
        if measure_versions is not None:
            measures.extend(self._get_measures(measure_versions, limit=limit))

        if limit is not None and len(measures) >= limit:
            return measures

        measure_ids = self.connection.get_all_measure_ids()
        for measure_id in measure_ids:
            if not _filter.is_allowed_measure_id(measure_id):
                continue

            version_ids = self.connection.get_measure_versions(measure_id)
            measures.extend(
                self._get_measures(
                    version_ids,
                    _filter,
                    limit - len(measures) if limit is not None else limit
                )
            )

            if limit is not None and len(measures) >= limit:
                break

        return measures

    def build(
        self,
        file_name: str,
        measure_versions: list[str] | None = None,
        _filter: MeasureFilter | None = None,
        limit: int | None = None
    ) -> None:
        dir_path = os.path.join(_ROOT, "..", "summaries")
        measure_pdf = MeasureSummary(
            dir_path=dir_path,
            connection=self.connection,
            file_name=file_name
        )

        measures = self.get_measures(
            measure_versions=measure_versions,
            _filter=_filter or MeasureFilter(),
            limit=limit
        )
        for measure in measures:
            measure_pdf.add_measure(measure)

        measure_pdf.build()
        logger.info(f"Summary {measure_pdf.file_name} was successfully created")


def build(
    file_name: str,
    all_measures: bool = False,
    measure_versions: list[str] | None = None,
    use_categories: list[str] | None = None,
    min_start_date: dt.datetime | None = None,
    max_start_date: dt.datetime | None = None,
    min_end_date: dt.datetime | None = None,
    max_end_date: dt.datetime | None = None,
    limit: int | None = None
) -> None:
    if all_measures:
        use_categories = list(lookups.USE_CATEGORIES.keys())

    _filter = MeasureFilter(
        use_categories=use_categories,
        min_start_date=min_start_date,
        max_start_date=max_start_date,
        min_end_date=min_end_date,
        max_end_date=max_end_date
    )

    builder = Builder()
    start = time.time()
    builder.build(
        file_name,
        measure_versions=measure_versions,
        _filter=_filter,
        limit=limit
    )
    elapsed = time.time() - start
    logger.info(f"Summary generation took {elapsed}s")
