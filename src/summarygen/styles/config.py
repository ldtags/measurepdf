__all__ = [
    "PAGESIZE",
    "X_MARGIN",
    "Y_MARGIN",
    "INNER_WIDTH",
    "INNER_HEIGHT",
    "DEFAULT_FONT_SIZE",
    "DEFAULT_FONT_NAME",
    "NL_HEIGHT"
]


from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter


PAGESIZE = letter
X_MARGIN = 0.45 * inch
Y_MARGIN = 1 * inch
INNER_WIDTH = PAGESIZE[0] - X_MARGIN * 2 - 12
INNER_HEIGHT = PAGESIZE[1] - Y_MARGIN * 2
DEFAULT_FONT_SIZE = 10
DEFAULT_FONT_NAME = 'SourceSansPro'
NL_HEIGHT = 0.3 * inch
