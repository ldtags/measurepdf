from configparser import ConfigParser

from context import resources, etrm, measurepdf


def test():
    config = ConfigParser()
    config.read(resources.get_path('config.ini'))
    connection = etrm.ETRMConnection(config['etrm']['type'] + ' ' + config['etrm']['token'])
    measure_pdf = measurepdf.MeasurePdf(relative_dir='summaries', override=True)
    measure_pdf.add_measure(connection.get_measure('SWAP001-03'))
    measure_pdf.build()


if __name__ == '__main__':
    test()
