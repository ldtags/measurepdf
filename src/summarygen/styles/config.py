from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

from src.summarygen.styles.enums import Alignment


PAGESIZE = letter
X_MARGIN = 0.45 * inch
Y_MARGIN = 1 * inch
INNER_WIDTH = PAGESIZE[0] - X_MARGIN * 2 - 12
INNER_HEIGHT = PAGESIZE[1] - Y_MARGIN * 2
NL_HEIGHT = 0.3 * inch
DEFAULT_FONT_SIZE = 10
DEFAULT_FONT_NAME = "SourceSansPro"
DEFAULT_INDENT_LEVEL = 0
DEFAULT_INDENT_SIZE = 30
DEFAULT_BULLET_INDENT_SIZE = 11
DEFAULT_SPACE_BEFORE = 0
DEFAULT_SPACE_AFTER = 0
DEFAULT_ALIGNMENT = Alignment.Left
