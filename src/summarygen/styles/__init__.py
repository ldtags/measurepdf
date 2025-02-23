__all__ = [
    "COLORS",
    "INNER_HEIGHT",
    "INNER_WIDTH",
    "PAGESIZE",
    "X_MARGIN",
    "Y_MARGIN",
    "DEFAULT_FONT_NAME",
    "DEFAULT_FONT_SIZE",
    "NL_HEIGHT",
    "Font",
    "FontType",
    "ParagraphStyle",
    "TableStyle",
    "STYLES",
    "PSTYLES",
    "TSTYLES",
    "DEF_PSTYLE",
    "get_table_style",
    "get_list_style"
]


from .colors import COLORS
from .config import (
    INNER_HEIGHT,
    INNER_WIDTH,
    PAGESIZE,
    X_MARGIN,
    Y_MARGIN,
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE,
    NL_HEIGHT
)
from .objects import (
    Font,
    FontType,
    ParagraphStyle,
    TableStyle
)
from .stylesheets import (
    STYLES,
    PSTYLES,
    TSTYLES,
    DEF_PSTYLE,
    get_table_style,
    get_list_style
)


__SourceSansPro = Font("SourceSansPro", "source-sans-pro")
__SourceSansPro.register_family()
__SourceSansPro.register(FontType.Black, FontType.BlackItalic)

__Merriweather = Font("Merriweather", "merriweather")
__Merriweather.register_family()
__Merriweather.register(FontType.Light, FontType.LightItalic)

__Helvetica = Font("Helvetica", "helvetica")
__Helvetica.register_family()

__Arial = Font("Arial", "arial")
__Arial.register_family()

__TimesNewRoman = Font("TimesNewRoman", "times-new-roman")
__TimesNewRoman.register_family()
