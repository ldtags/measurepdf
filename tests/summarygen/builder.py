import os
import sys
import time
import logging
import argparse as ap
import datetime as dt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import lookups, resources, _ROOT
from src.etrm import ETRMConnection
from src.summarygen import MeasureSummary


logger = logging.getLogger(__name__)


class TestBuilder:
    def __init__(self):
        api_key = resources.get_api_key(role="user")
        self.connection = ETRMConnection(api_key, use_persistent_cache=True)

    def build(
        self,
        file_name: str,
        measure_versions: list[str] | str | None = None,
        use_categories: list[str] | str | None = None,
        min_start_date: dt.date | None = None,
        max_start_date: dt.date | None = None,
        min_end_date: dt.date | None = None,
        max_end_date: dt.date | None = None
    ) -> None:
        dir_path = os.path.join(_ROOT, "..", "summaries")
        measure_pdf = MeasureSummary(
            dir_path=dir_path,
            connection=self.connection,
            file_name=file_name
        )

        logger.info("Summary builder successfully created")

        measure_versions = measure_versions or []
        if isinstance(measure_versions, str):
            measure_versions = [measure_versions]

        for version_id in measure_versions:
            logger.info(f"Adding measure: {version_id}")
            measure_pdf.add_measure(version_id)

        use_categories = use_categories or []
        if isinstance(use_categories, str):
            use_categories = [use_categories]

        for use_category in use_categories:
            logger.info(f"Adding use category: {use_category}")
            measure_pdf.add_use_category(use_category)

        measure_pdf.filter_measures(
            min_start_date=min_start_date,
            max_start_date=max_start_date,
            min_end_date=min_end_date,
            max_end_date=max_end_date
        )
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


if __name__ == '__main__':
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
    builder = TestBuilder()
    builder.build(
        name,
        measure_versions=measures,
        use_categories=use_categories,
        min_start_date=getattr(args, "--min-start-date", None),
        max_start_date=getattr(args, "--max-start-date", None),
        min_end_date=getattr(args, "--min-end-date", None),
        max_end_date=getattr(args, "--max-end-date", None)
    )
    elapsed = time.time() - start
    logger.info(f"Summary generation took {elapsed}s")
