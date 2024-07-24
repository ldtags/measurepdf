import unittest as ut

from tests.utils import misc


def suites() -> list[ut.TestSuite]:
    return [
        misc.suite()
    ]


if __name__ == '__main__':
    runner = ut.TextTestRunner()
    for suite in suites():
        runner.run(suite)
