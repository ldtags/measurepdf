import unittest as ut

from tests.etrm import connection


def suites() -> list[ut.TestSuite]:
    return [
        connection.suite()
    ]


if __name__ == '__main__':
    runner = ut.TextTestRunner()
    for suite in suites():
        runner.run(suite)
