import os
import re
import sys
import time
import argparse as ap
from typing import Literal
from configparser import ConfigParser

from context import src, etrm, summarygen, resources


MEASURES = [
    'SWFS006-03',
    # embedded value table with no cids

    'SWFS001-03',
    # embedded value table with cids

    'SWHC045-03',
    # static value table with no spanning

    'SWWH025-07',
    # medium-sized subscript
    # unscaled images
    # list

    'SWFS017-03',
    # static value table with column spans and row spans
    # single digit superscript
    # image rescaling
    # list

    'SWFS010-03',
    # edge case for measure details table column wrapping
]

def get_api_key(role: Literal['user', 'admin']='user') -> str:
    match role:
        case 'user':
            source = 'etrm'
        case 'admin':
            source = 'etrm-admin'
        case other:
            raise RuntimeError(f'invalid eTRM role: {other}')

    config = ConfigParser()
    config.read(resources.get_path('config.ini'))
    token_type = config[source]['type']
    token = config[source]['token']
    return f'{token_type} {token}'


class TestBuilder:
    def __init__(self,
                 version_ids: list[str]=[],
                 use_categories: list[str]=[]):
        api_key = get_api_key(role='user')
        self.connection = etrm.ETRMConnection(api_key)
        self.version_ids = version_ids
        self.use_categories = use_categories

    def is_empty(self) -> bool:
        return (
            self.version_ids == []
                and self.use_categories == []
        )

    def build_summary(self):
        if self.is_empty():
            return

        dir_path = os.path.join(src._ROOT, '..', 'summaries')
        measure_pdf = summarygen.MeasureSummary(dir_path, self.connection)
        print('measure pdf object created', file=sys.stderr)

        for measure in self.version_ids:
            measure_pdf.add_measure(measure)

        for use_category in self.use_categories:
            measure_pdf.add_use_category(use_category)

        measure_pdf.build()
        print(f'measure summary {measure_pdf.file_name} was successfully created')

    def run(self):
        start = time.time()
        self.build_summary()
        elapsed = time.time() - start
        print(f'took {elapsed}s', file=sys.stderr)


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

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    measures = getattr(args, 'measures', [])
    use_categories = getattr(args, 'use_category', [])
    builder = TestBuilder(measures, use_categories)
    builder.run()
