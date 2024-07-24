import unittest as ut


def suites() -> list[ut.TestSuite]:
    return [

    ]


if __name__ == '__main__':
    runner = ut.TextTestRunner()
    for suite in suites():
        runner.run(suite)
