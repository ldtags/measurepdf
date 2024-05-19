import argparse
import configparser

import src.resources as resources
from src.app import Controller


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='eTRM Measure Summary Tool',
        description='Creates a summary of one or more measures.')

    parser.add_argument('-m', '--mode',
        metavar='mode',
        type=str,
        choices=['client', 'dev'],
        default='client',
        help='specify which mode to run the app in (default: client)')

    return parser.parse_args()


def app_controller(mode: str) -> Controller:
    controller = Controller()
    if mode == 'dev':
        config = configparser.ConfigParser()
        config.read(resources.get_path('config.ini'))
        auth_token = config['etrm-admin']['type'] + ' ' + config['etrm-admin']['token']
        controller.connect(auth_token)
    return controller


def main():
    args = parse_args()
    mode: str = getattr(args, 'mode', 'client')
    controller = app_controller(mode)
    controller.start()    


if __name__ == '__main__':
    main()
