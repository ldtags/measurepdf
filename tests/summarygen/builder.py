import os
import sys
import time
import logging
import argparse as ap

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src import utils, lookups, _ROOT
from src.etrm import ETRMConnection
from src.summarygen import MeasureSummary


logger = logging.getLogger(__name__)


class TestBuilder:
    def __init__(self):
        api_key = utils.get_api_key(role='user')
        self.connection = ETRMConnection(api_key)

    def build(
        self,
        file_name: str,
        measure_versions: list[str] | str | None = None,
        use_categories: list[str] | str | None = None
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

        measure_pdf.build()
        logger.info(f"Summary {measure_pdf.file_name} was successfully created")


def parse_args() -> ap.Namespace:
    parser = ap.ArgumentParser(
        prog="eTRM Measure to PDF Tester",
        description="Tests the eTRM measure summary generation process and package integrations."
    )

    parser.add_argument(
        '-m', '--measures',
        metavar='measures',
        nargs='*',
        default=[],
        help="Specifies the measure or measures to generate a summary for."
    )

    parser.add_argument(
        "-u", "--use-category",
        metavar="use_category",
        nargs="*",
        default=[],
        help="Specifies the use category or categories to generate a summary for."
    )

    parser.add_argument(
        "-n", "--name",
        metavar="name",
        default="measure_summary",
        help="Specifies the name of the generated summary file."
    )

    parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Include to generate a summary that includes every measure in each use category."
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Include to run the program in debug mode."
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    measures = getattr(args, 'measures', [])
    use_categories = getattr(args, 'use_category', [])
    name = getattr(args, 'name', 'measure_summary')
    _all = getattr(args, 'all', False)
    if _all and (measures or use_categories):
        print('Usage: ./cli [-a | -m -u -n]')
        exit(1)

    builder = TestBuilder()
    start = time.time()
    if _all:
        blacklist = ['WB']
        use_categories = list(lookups.USE_CATEGORIES.keys())
        for use_category in use_categories:
            if use_category in blacklist:
                continue
            
            print(f'Building summary for {use_category}')
            builder.build(
                f'SW{use_category}_Summary',
                use_categories=use_category
            )
    else:
        builder.build(
            name,
            measure_versions=measures,
            use_categories=use_categories
        )

    elapsed = time.time() - start
    print(f'took {elapsed}s', file=sys.stderr)
