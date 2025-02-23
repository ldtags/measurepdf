from typing import Literal


_TableSpan = tuple[tuple[int, int], tuple[int, int]]
"""Represents a row/col span in a table

The first tuple contains the (y, x) coords of the span

The second tuple contains the (row, col) span sizes
"""


_TableOrient = Literal["top", "left", "top-left"]
"""Represents the orientation of the table.

This determines whether the header of the table is on either
the `top`, `left`, or both `top` and `left` sides of the table.
"""
