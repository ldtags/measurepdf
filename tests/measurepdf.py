from configparser import ConfigParser

from src.etrm import ETRMConnection
from src.measurepdf import MeasurePdf
from resources import get_path


def test():
    config = ConfigParser()
    config.read(get_path('config.ini'))
    connection = ETRMConnection(config['etrm']['type'] + ' ' + config['etrm']['token'])
    measure_pdf = MeasurePdf()
    measure_pdf.add_measure(connection.get_measure('SWAP001-03'))
