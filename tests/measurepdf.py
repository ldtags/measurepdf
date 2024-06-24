import os
import sys
import time
from configparser import ConfigParser

from context import resources, etrm, summary, _ROOT


config = ConfigParser()
config.read(resources.get_path('config.ini'))
connection = etrm.ETRMConnection(config['etrm']['type'] + ' ' + config['etrm']['token'])


def build_summary(measure_ids: list[str]):
    dir_path = os.path.join(_ROOT, '..', 'summaries')
    measure_pdf = summary.MeasureSummary(dir_path)
    print('measure pdf object created', file=sys.stderr)

    for measure_id in measure_ids:
        measure_pdf.add_measure(connection.get_measure(measure_id))
        print(f'added measure {measure_id}', file=sys.stderr)

    measure_pdf.build()
    print(f'measure summary {measure_pdf.file_name} was successfully created')


def test(measures: list[str]):
    start = time.time()
    build_summary(measures)
    elapsed = time.time() - start
    print(f'took {elapsed}s', file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Cannot run the measurepdf module test without measures',
              file=sys.stderr)
        exit(1)
    test(sys.argv[1:])
