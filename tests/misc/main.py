import unittest as ut

from tests.misc import utils


def suites() -> list[ut.TestSuite]:
    return [
        utils.suite()
    ]


if __name__ == '__main__':
    runner = ut.TextTestRunner()
    for suite in suites():
        runner.run(suite)
