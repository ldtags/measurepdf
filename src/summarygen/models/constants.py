from src.summarygen.models.enums import Alignment
from src.summarygen.models.general import BulletOption


# Default stylings
DEFAULT_INDENT_LEVEL = 0
DEFAULT_INDENT_SIZE = 35
DEFAULT_BULLET_INDENT_SIZE = 11
DEFAULT_SPACE_BEFORE = 0
DEFAULT_SPACE_AFTER = 0
DEFAULT_ALIGNMENT = Alignment.Left

# Pre-defined bullet point options
SQUARE_BULLET = BulletOption([u"\u25a0"])
DASH_BULLET = BulletOption([u"\u2014"])
CIRCLE_BULLET = BulletOption(["\u25cf", "\u25cb"])
