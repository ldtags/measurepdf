import argparse
from argparse import (
    Namespace
)

from src.app import AppController


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        prog='eTRM Measure to PDF',
        description='Creates a PDF with data from one or more measures.')

    parser.add_argument('-m', '--mode',
        metavar='mode',
        choices=['client', 'dev'],
        default='client',
        help='specify the run mode of this application (default: client)')

    return parser.parse_args()


def main():
    args = parse_args()
    mode = getattr(args, 'mode')
    main_app = AppController()
    main_app.run(mode)


if __name__ == '__main__':
    main()
