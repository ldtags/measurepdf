import sys
from configparser import ConfigParser

from context import resources, etrm, measurepdf


config = ConfigParser()
config.read(resources.get_path('config.ini'))
connection = etrm.ETRMConnection(config['etrm']['type'] + ' ' + config['etrm']['token'])


def build_summary(measure_ids: list[str]):
    measure_pdf = measurepdf.MeasurePdf(relative_dir='summaries', override=True)
    print('measure pdf object created', file=sys.stderr)

    for measure_id in measure_ids:
        measure_pdf.add_measure(connection.get_measure(measure_id))
        print(f'added measure {measure_id}', file=sys.stderr)

    measure_pdf.build()
    print(f'measure summary {measure_pdf.file_name} was successfully created')


def test():
    build_summary(['SWAP001-03'])


if __name__ == '__main__':
    test()
