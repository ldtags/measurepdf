from enum import Enum


class Alignment(Enum):
    Left = "Left"
    Center = "Center"
    Right = "Right"


class FontType(Enum):
    Regular = ''
    Italic = 'I'
    Bold = 'B'
    BoldItalic = 'BI'
    SemiBold = 'SB'
    SemiBoldItalic = 'SBI'
    ExtraBold = "EB"
    ExtraBoldItalic = "EBI"
    Light = 'L'
    LightItalic = 'LI'
    ExtraLight = 'EL'
    ExtraLightItalic = 'ELI'
    Black = 'Bl'
    BlackItalic = 'BlI'
    Math = 'M'
