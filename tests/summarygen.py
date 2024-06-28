import os
import sys
import time
from configparser import ConfigParser

from src import resources, _ROOT
from src.etrm import ETRMConnection
from src.summarygen import MeasureSummary


config = ConfigParser()
config.read(resources.get_path('config.ini'))
connection = ETRMConnection(config['etrm']['type'] + ' ' + config['etrm']['token'])


def build_summary(measure_ids: list[str]):
    dir_path = os.path.join(_ROOT, '..', 'summaries')
    measure_pdf = MeasureSummary(dir_path, connection)
    print('measure pdf object created', file=sys.stderr)

    for measure_id in measure_ids:
        measure_pdf.add_measure(connection.get_measure(measure_id))
        print(f'added measure {measure_id}', file=sys.stderr)

    measure_pdf.build()
    print(f'measure summary {measure_pdf.file_name} was successfully created')


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


def test():
    start = time.time()
    build_summary(MEASURES)
    elapsed = time.time() - start
    print(f'took {elapsed}s', file=sys.stderr)


if __name__ == '__main__':
    test()