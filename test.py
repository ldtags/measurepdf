import sys
import os
import argparse as ap

from tests import measurepdf, _utils


MODULES = ['measurepdf', '_utils', 'etrm']
UNIT_TEST = {
    'measurepdf': measurepdf.test,
    '_utils': _utils.test
}


def parse_args() -> ap.Namespace:
    parser = ap.ArgumentParser(
        prog='eTRM Measure to PDF Tester',
        description='Tests modules and integration in the eTRM ')

    parser.add_argument('-u', '--unit',
        metavar='unit_modules',
        nargs='*',
        type=str,
        help='specify the modules to unit test')


if __name__ == '__main__':
    args = parse_args()
    unit_modules = getattr(args, 'unit_modules', None)
    if unit_modules != None:
        if isinstance(unit_modules, str):
            unit_modules = [unit_modules]

        if not isinstance(unit_modules, list[str]):
            print('usage: main.py -m <module name> ...]', file=sys.stderr)
            sys.exit(os.EX_OK)

        if 'all' in unit_modules:
            unit_modules = MODULES
        else:
            for module in unit_modules:
                if module not in MODULES:
                    print(f'unknown module: {module}', file=sys.stderr)
                    print(f'supported modules - {MODULES}', file=sys.stderr)
                    sys.exit(os.EX_OK)

        for module in unit_modules:
            UNIT_TEST[module]()
        
