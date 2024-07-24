import unittest as ut

from tests.summarygen import rlobjects


MEASURES = [
    'SWFS006-03',
    # embedded value table with no cids

    'SWFS001-03',
    # embedded value table with cids

    'SWHC045-03',
    # static value table with no spanning

    'SWWH025-07',
    # medium-sized subscript
    # unscaled images
    # list

    'SWFS017-03',
    # static value table with column spans and row spans
    # single digit superscript
    # image rescaling
    # list

    'SWFS010-03',
    # edge case for measure details table column wrapping
]


def suites() -> list[ut.TestSuite]:
    return [
        rlobjects.suite()
    ]


if __name__ == '__main__':
    runner = ut.TextTestRunner()
    for suite in suites():
        runner.run(suite)
