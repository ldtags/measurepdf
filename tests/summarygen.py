import os
import re
import sys
import time
import argparse as ap
from typing import Literal
from configparser import ConfigParser

from context import src, etrm, summarygen, resources, exceptions, patterns


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
                 measure_version_ids: list[str]=[],
                 use_categories: list[str]=[]):
        api_key = get_api_key(role='user')
        self.connection = etrm.ETRMConnection(api_key)
        self.measures: list[etrm.models.Measure] = []

        measure_versions = set(measure_version_ids)
        measure_ids = set()
        for use_category in use_categories:
            print(f'getting measure ids for use category: {use_category}')
            try:
                uc_ids = self.connection.get_all_measure_ids(use_category=use_category)
                for uc_id in uc_ids:
                    measure_ids.add(uc_id)
            except exceptions.ETRMConnectionError as err:
                print(f'error message: {err.message}')

        for measure_id in measure_ids:
            print(f'getting versions of measure: {measure_id}')
            try:
                versions = self.connection.get_measure_versions(measure_id)
            except exceptions.ETRMResponseError:
                continue
            versions.sort(key=self.__version_key, reverse=True)
            for version in versions:
                if version.count('-') == 1:
                    measure_versions.add(version)
                    break

        measure_versions = list(measure_versions)
        if len(measure_versions) == 0:
            measure_versions = set(MEASURES)
        else:
            measure_versions.sort(key=self.__version_key, reverse=True)

        for measure_id in measure_versions:
            print(f'getting measure: {measure_id}')
            try:
                measure = self.connection.get_measure(measure_id)
            except exceptions.ETRMConnectionError as err:
                print(f'error message: {err.message}')
            self.measures.append(measure)

    def __version_key(self, full_version_id: str) -> int:
        """Sorting key for measure versions."""

        re_match = re.search(patterns.VERSION_ID, full_version_id)
        if re_match == None:
            return -1

        key = 0
        statewide_id = re_match.group(2)
        version_id = re_match.group(3)

        re_match = re.search(patterns.STWD_ID, statewide_id)
        if re_match == None:
            return -1

        measure_type = re_match.group(2)
        key += sum([ord(c) * -1000 for c in measure_type])
        use_category = re_match.group(3)
        key += sum([ord(c) * -1000 for c in use_category])

        uc_version = re_match.group(4)
        key += int(uc_version) * -100

        try:
            version, _ = version_id.split('-', 1)
            version = int(version)
            draft = 0
        except ValueError:
            version = int(version_id)
            draft = 1

        key += version * 10
        key += draft
        return key

    def build_summary(self):
        dir_path = os.path.join(src._ROOT, '..', 'summaries')
        measure_pdf = summarygen.MeasureSummary(dir_path, self.connection)
        print('measure pdf object created', file=sys.stderr)

        if len(self.measures) == 0:
            return

        for measure in self.measures:
            measure_pdf.add_measure(measure)

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
