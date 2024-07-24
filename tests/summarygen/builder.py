import os
import sys
import time
import datetime
import argparse as ap

from src import utils, lookups, _ROOT
from src.etrm import ETRMConnection
from src.summarygen import MeasureSummary


class TestBuilder:
    def __init__(self):
        api_key = utils.get_api_key(role='user')
        self.connection = ETRMConnection(api_key)

    def build(self,
              file_name: str,
              measure_versions: list[str] | str | None=None,
              use_categories: list[str] | str | None=None):
        dir_path = os.path.join(_ROOT, '..', 'summaries')
        measure_pdf = MeasureSummary(dir_path=dir_path,
                                     connection=self.connection,
                                     file_name=file_name)
        print('measure pdf object created', file=sys.stderr)

        measure_versions = measure_versions or []
        if isinstance(measure_versions, str):
            measure_versions = [measure_versions]

        for version_id in measure_versions:
            measure_pdf.add_measure(version_id)

        use_categories = use_categories or []
        if isinstance(use_categories, str):
            use_categories = [use_categories]

        for use_category in use_categories:
            measure_pdf.add_use_category(use_category)

        measure_pdf.filter_measures(
            min_end_date=datetime.date(2024, 1, 1)
        )
        measure_pdf.build()
        print(f'measure summary {measure_pdf.file_name} was successfully created')


def parse_args() -> ap.Namespace:
    parser = ap.ArgumentParser(
        prog='eTRM Measure to PDF Tester',
        description='Tests modules and integration in the eTRM '
    )

    parser.add_argument(
        '-m', '--measures',
        metavar='measures',
        nargs='*',
        default=[],
        help='specify the measures to build a summary for'
    )

    parser.add_argument(
        '-u', '--use-category',
        metavar='use_category',
        nargs='*',
        default=[],
        help='specify use categories to build a summary for'
    )

    parser.add_argument(
        '-n', '--name',
        metavar='name',
        default='measure_summary',
        help='specify the name of the generated file'
    )

    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='include to generate several summaries of each use category'
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
            builder.build(f'SW{use_category}_Summary',
                          use_categories=use_category)
    else:
        builder.build(name,
                      measure_versions=measures,
                      use_categories=use_categories)

    elapsed = time.time() - start
    print(f'took {elapsed}s', file=sys.stderr)
