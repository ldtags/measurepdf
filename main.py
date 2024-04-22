import argparse
import configparser

from src.app import AppController
import resources


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


def main():
    args = parse_args()
    mode: str = getattr(args, 'mode', 'client')
    controller = AppController()
    if mode == 'dev':
        config = configparser.ConfigParser()
        config.read(resources.get_path('config.ini'))
        controller.connect(f'{config["etrm"]["type"]} {config["etrm"]["token"]}')
    controller.run()


if __name__ == '__main__':
    main()
