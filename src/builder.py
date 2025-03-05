import os
import re
import sys
import time
import logging
import warnings
import argparse as ap
import datetime as dt

from src import lookups, resources, patterns, utils, _ROOT
from src.etrm import ETRMConnection, Measure
from src.summarygen import MeasureSummary


logger = logging.getLogger(__name__)


class Builder:
    def __init__(self, api_key: str | None = None):
        _api_key = api_key or resources.get_api_key(role="user")
        self.connection = ETRMConnection(_api_key, use_persistent_cache=True)

    def _get_measures(
        self,
        version_ids: list[str] | None = None,
        min_start_date: dt.date | None = None,
        max_start_date: dt.date | None = None,
        min_end_date: dt.date | None = None,
        max_end_date: dt.date | None = None,
        limit: int | None = None        
    ) -> list[Measure]:
        measures: list[Measure] = []
        version_ids.sort(key=utils.version_key)
        for version_id in version_ids:
            measure = self.connection.get_measure(version_id)
            if min_start_date is not None and measure.start_date < min_start_date:
                continue

            if max_start_date is not None and measure.start_date >= max_start_date:
                continue

            if (min_end_date is not None
                    and measure.end_date is not None
                    and measure.end_date < min_end_date):
                continue

            if (max_end_date is not None
                    and measure.end_date is not None
                    and measure.end_date >= max_end_date):
                continue

            measures.append(measure)
            if limit is not None and len(measures) >= limit:
                break

        return measures

    def get_measures(
        self,
        measure_versions: list[str] | None = None,
        use_categories: list[str] | None = None,
        min_start_date: dt.date | None = None,
        max_start_date: dt.date | None = None,
        min_end_date: dt.date | None = None,
        max_end_date: dt.date | None = None,
        limit: int | None = None
    ) -> list[Measure]:
        logger.info("Adding measures...")
        logger.info(f"\tMeasure Versions: {measure_versions}")
        logger.info(f"\tUse Categories  : {use_categories}")
        logger.info(f"\tMin Start Date  : {min_start_date}")
        logger.info(f"\tMax Start Date  : {max_start_date}")
        logger.info(f"\tMin End Date    : {min_end_date}")
        logger.info(f"\tMax End Date    : {max_end_date}")
        logger.info(f"\tLimit           : {limit}")

        measures: list[Measure] = []
        if measure_versions is not None:
            measures.extend(
                self._get_measures(
                    measure_versions,
                    min_start_date,
                    max_start_date,
                    min_end_date,
                    max_end_date,
                    limit
                )
            )

        if limit is not None and len(measures) >= limit:
            return measures

        measure_ids = self.connection.get_all_measure_ids()
        for measure_id in measure_ids:
            re_match = re.fullmatch(patterns.STWD_ID, measure_id)
            if re_match is None:
                warnings.warn(f"Invalid statewide ID [{measure_id}], skipping...", RuntimeWarning)
                continue

            try:
                measure_use_category = str(re_match.group(3))
            except ValueError:
                warnings.warn(f"Invalid use category in {measure_id}, skipping...", RuntimeWarning)
                continue

            if use_categories is not None and measure_use_category not in use_categories:
                continue

            version_ids = self.connection.get_measure_versions(measure_id)
            measures.extend(
                self._get_measures(
                    version_ids,
                    min_start_date,
                    max_start_date,
                    min_end_date,
                    max_end_date,
                    limit - len(measures) if limit is not None else limit
                )
            )

            if limit is not None and len(measures) >= limit:
                break

        return measures

    def build(
        self,
        file_name: str,
        measure_versions: list[str] | str | None = None,
        use_categories: list[str] | str | None = None,
        min_start_date: dt.date | None = None,
        max_start_date: dt.date | None = None,
        min_end_date: dt.date | None = None,
        max_end_date: dt.date | None = None,
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
            use_categories=use_categories,
            min_start_date=min_start_date,
            max_start_date=max_start_date,
            min_end_date=min_end_date,
            max_end_date=max_end_date,
            limit=limit
        )
        for measure in measures:
            measure_pdf.add_measure(measure)

        measure_pdf.build()
        logger.info(f"Summary {measure_pdf.file_name} was successfully created")


def parse_args() -> ap.Namespace:
    parser = ap.ArgumentParser(
        prog="eTRM Measure to PDF Tester",
        description="Tests the eTRM measure summary generation process and package integrations."
    )

    parser.add_argument(
        "-m", "--measures",
        metavar="measures",
        nargs="*",
        default=[],
        help="Specifies the measure or measures to generate a summary for."
    )

    parser.add_argument(
        "-u", "--use-categories",
        metavar="use_categories",
        nargs="*",
        default=[],
        help="Specifies the use category or categories to generate a summary for."
    )

    parser.add_argument(
        "-o", "--output-file",
        metavar="output_file",
        default="measure_summary",
        help="Specifies the name of the generated summary file."
    )

    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Include to generate a summary that includes every measure in each use category."
    )

    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=None,
        help="Specifies an upper limit of measures to generate a summary from."
    )

    parser.add_argument(
        "--min-start-date",
        type=dt.date.fromisoformat,
        default=None,
        help="Specifies the inclusive minimum start date (in ISO format) to filter measures by."
    )

    parser.add_argument(
        "--max-start-date",
        type=dt.date.fromisoformat,
        default=None,
        help="Specifies the non-inclusive maximum start date (in ISO format) to filter measures by."
    )

    parser.add_argument(
        "--min-end-date",
        type=dt.date.fromisoformat,
        default=None,
        help="Specifies the inclusive minimum end date (in ISO format) to filter measures by."
    )

    parser.add_argument(
        "--max-end-date",
        type=dt.date.fromisoformat,
        default=None,
        help="Specifies the non-inclusive maximum end date (in ISO format) to filter measures by."
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    measures = getattr(args, "measures", [])
    use_categories = getattr(args, "use_categories", [])
    name = getattr(args, "output_file", "measure_summary")
    _all = getattr(args, "all", False)
    if _all and (measures != [] or use_categories != []):
        print("Usage: ./cli [-a | -m -u] ...")
        sys.exit(1)

    if _all:
        use_categories = list(lookups.USE_CATEGORIES.keys())

    start = time.time()
    builder = Builder()
    builder.build(
        name,
        measure_versions=measures,
        use_categories=use_categories,
        min_start_date=getattr(args, "min_start_date", None),
        max_start_date=getattr(args, "max_start_date", None),
        min_end_date=getattr(args, "min_end_date", None),
        max_end_date=getattr(args, "max_end_date", None),
        limit=getattr(args, "limit", None)
    )
    elapsed = time.time() - start
    logger.info(f"Summary generation took {elapsed}s")
