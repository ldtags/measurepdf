import sys
import os
import argparse as ap
import unittest as ut

from tests import misc, summarygen, etrm, app


MODULES = ['misc', 'summarygen', 'etrm', 'app']
TEST_SUITES = {
    'misc': misc.suites,
    'summarygen': summarygen.suites,
    'etrm': etrm.suites,
    'app': app.suites
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

    return parser.parse_args()


def main():
    args = parse_args()
    unit_modules = getattr(args, 'unit', None)
    if unit_modules != None:
        if not isinstance(unit_modules, list):
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

        test_suites: list[ut.TestSuite] = []
        for module in unit_modules:
            test_suites.extend(TEST_SUITES[module]())

        runner = ut.TextTestRunner()
        for test_suite in test_suites:
            runner.run(test_suite)


if __name__ == '__main__':
    main()
