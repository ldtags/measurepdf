__all__ = [
    "_TableSpan"
]


_TableSpan = tuple[tuple[int, int], tuple[int, int]]
"""Represents a row/col span in a table.

The first tuple contains the (y, x) coords of the span.

The second tuple contains the (row, col) span sizes.
"""
