from enum import Enum


class Alignment(Enum):
    Left = "Left"
    Center = "Center"
    Right = "Right"


class ElementType(Enum):
    Text = "Text"
    Space = "Space"
    Newline = "Newline"
    Reference = "Reference"
    TerminologyHeader = "TerminologyHeader"


class TextStyle(Enum):
    Normal = "Normal"
    Strong = "Strong"
    Italic = "Italic"
    Superscript = "Superscript"
    Subscript = "Subscript"
    Link = "Link"
    Pre = "Pre"
