from enum import Enum


class ElementType(Enum):
    """Defines several types of paragraph elements.

    Use this enum to specify elements that require custom styling and display.
    """

    Text = "Text"
    Space = "Space"
    Newline = "Newline"
    Reference = "Reference"
    TerminologyHeader = "TerminologyHeader"


class TextStyle(Enum):
    """Defines several types of text styles.

    Use this enum to add styling attributes to paragraph elements.
    """

    Normal = "Normal"
    Strong = "Strong"
    Italic = "Italic"
    Superscript = "Superscript"
    Subscript = "Subscript"
    Link = "Link"
    Pre = "Pre"
