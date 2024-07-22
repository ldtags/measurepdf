from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter


PAGESIZE = letter
X_MARGIN = 0.45 * inch
Y_MARGIN = 1 * inch
INNER_WIDTH = PAGESIZE[0] - X_MARGIN * 2 - 12
INNER_HEIGHT = PAGESIZE[1] - Y_MARGIN * 2
_DEF_FONT_SIZE = 10
_DEF_FONT_NAME = 'SourceSansPro'
_NL_HEIGHT = 0.3 * inch
