from configparser import ConfigParser

import context.resources as resources
from context.src import etrm
from context.src import measurepdf


def test():
    config = ConfigParser()
    config.read(resources.get_path('config.ini'))
    connection = etrm.ETRMConnection(config['etrm']['type'] + ' ' + config['etrm']['token'])
    measure_pdf = measurepdf.MeasurePdf(override=True)
    measure_pdf.add_measure(connection.get_measure('SWAP001-03'))
    measure_pdf.build()


if __name__ == '__main__':
    test()
