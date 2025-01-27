from __future__ import annotations
import os
import sys
from enum import Enum
from typing import Literal, TypeVar, Generic, Any, overload
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import PropertySet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import TableStyle as _TableStyle
from reportlab.rl_config import (
    underlineWidth as _baseUnderlineWidth,
    underlineOffset as _baseUnderlineOffset,
    underlineGap as _baseUnderlineGap,
    strikeWidth as _baseStrikeWidth,
    strikeOffset as _baseStrikeOffset,
    strikeGap as _baseStrikeGap,
    spaceShrinkage as _spaceShrinkage,
    platypus_link_underline as _platypus_link_underline,
    hyphenationLang as _hyphenationLang,
    uriWasteReduce as _uriWasteReduce,
    embeddedHyphenation as _embeddedHyphenation
)

from src import asset_path
from src.summarygen.styles.config import (
    _DEF_FONT_NAME,
    _DEF_FONT_SIZE
)
from src.summarygen.styles.colors import COLORS


class FontType(Enum):
    Regular = ''
    Italic = 'I'
    Bold = 'B'
    BoldItalic = 'BI'
    SemiBold = 'SB'
    SemiBoldItalic = 'SBI'
    Light = 'L'
    LightItalic = 'LI'
    ExtraLight = 'EL'
    ExtraLightItalic = 'ELI'
    Black = 'Bl'
    BlackItalic = 'BlI'


class Font:
    """Registerable font for the reportlab library

    Fonts must be stored in the `assets` directory as a directory named
    `asset_dir` that contains all font files

    Each font file must follow the name format `name`-`style`.ttf

    Font styles are case specific
    """

    def __init__(self, name: str, font_dir: str):
        self.name = name
        self.path = asset_path(font_dir, 'fonts')

    @overload
    def register(self, font_type: FontType) -> TTFont:
        ...

    @overload
    def register(self, *font_types: FontType) -> list[TTFont]:
        ...

    def register(self, *font_types: FontType) -> TTFont | list[TTFont]:
        fonts: list[TTFont] = []
        for font_type in font_types:
            font = TTFont(
                f'{self.name}{font_type.value}',
                os.path.join(self.path, f'{self.name}-{font_type.name}.ttf')
            )
            fonts.append(font)
            pdfmetrics.registerFont(font)

        if len(fonts) == 1:
            return fonts[0]

        return fonts

    def register_family(self):
        """Registers `Regular`, `Bold`, `Italic`, and `BoldItalic` for the font family.

        Any other font faces must be registered manually via `register`.
        """

        regular = self.register(FontType.Regular)
        bold = self.register(FontType.Bold)
        italic = self.register(FontType.Italic)
        bold_italic = self.register(FontType.BoldItalic)
        registerFontFamily(
            self.name,
            normal=regular.fontName,
            bold=bold.fontName,
            italic=italic.fontName,
            boldItalic=bold_italic.fontName
        )


class ParagraphStyle(PropertySet):
    defaults = {
        'fontName': _DEF_FONT_NAME,
        'fontSize': _DEF_FONT_SIZE,
        'leading': _DEF_FONT_SIZE * 1.2,
        'leftIndent': 0,
        'rightIndent': 0,
        'firstLineIndent': 0,
        'alignment': TA_LEFT,
        'spaceBefore': 0,
        'spaceAfter': 0,
        'bulletFontName': _DEF_FONT_NAME,
        'bulletFontSize': _DEF_FONT_SIZE,
        'bulletIndent': 0,
        'textColor': colors.black,
        'backColor': None,
        'wordWrap': None,
        'borderWidth': 0,
        'borderPadding': 0,
        'borderColor': None,
        'borderRadius': None,
        'allowWidows': 1,
        'allowOrphans': 0,
        'textTransform': None,
        'endDots': None,
        'splitLongWords': 1,
        'underlineWidth': _baseUnderlineWidth,
        'bulletAnchor': 'start',
        'justifyLastLine': 0,
        'justifyBreaks': 0,
        'spaceShrinkage': _spaceShrinkage,
        'strikeWidth': _baseStrikeWidth,
        'underlineOffset': _baseUnderlineOffset,
        'underlineGap': _baseUnderlineGap,
        'strikeOffset': _baseStrikeOffset,
        'strikeGap': _baseStrikeGap,
        'linkUnderline': _platypus_link_underline,
        'underlineColor':   None,
        'strikeColor': None,
        'hyphenationLang': _hyphenationLang,
        'embeddedHyphenation': _embeddedHyphenation,
        'uriWasteReduce': _uriWasteReduce,
    }

    def __init__(self,
                 name: str,
                 parent: PropertySet | None=None,
                 font_name: str | None=None,
                 font_size: float | None=None,
                 leading: float | None=None,
                 sub_size: float | None=None,
                 sup_size: float | None=None,
                 text_color: colors.Color | None=None,
                 left_indent: float | None=None,
                 right_indent: float | None=None,
                 space_before: float | None=None,
                 space_after: float | None=None,
                 word_wrap: Literal['CJK', 'LTR', 'RTL'] | None=None,
                 **kwargs):
        if font_name is not None:
            kwargs['fontName'] = font_name
        
        if font_size is not None:
            kwargs['fontSize'] = font_size
            if leading is None:
                kwargs['leading'] = font_size * 1.2
        
        if leading is not None:
            kwargs['leading'] = leading

        if text_color is not None:
            kwargs['textColor'] = text_color

        if word_wrap is not None:
            kwargs['wordWrap'] = word_wrap

        if left_indent is not None:
            kwargs['leftIndent'] = left_indent
        
        if right_indent is not None:
            kwargs['rightIndent'] = right_indent
        
        if space_before is not None:
            kwargs['spaceBefore'] = space_before
        
        if space_after is not None:
            kwargs['spaceAfter'] = space_after

        PropertySet.__init__(self,
                             name=name,
                             parent=parent,
                             **kwargs)

        self.sub_size = sub_size or self['fontSize'] * (2 / 3)
        self.sup_size = sup_size or self['fontSize'] * (2 / 3)
        self.x_padding = self['leftIndent'] + self['rightIndent']
        self.y_padding = self['spaceBefore'] + self['spaceAfter']

    def __getitem__(self, key: str) -> Any:
        return self.__dict__[key]

    def __setitem__(self, key: str, val: Any) -> None:
        assert key in self.defaults.keys()
        self.__dict__[key] = val

    @property
    def font_name(self) -> str:
        font_name = self['fontName']
        assert isinstance(font_name, str)
        return font_name

    @font_name.setter
    def font_name(self, name: str) -> None:
        self['fontName'] = name

    @property
    def font_size(self) -> float:
        font_size = self['fontSize']
        assert isinstance(font_size, float | int)
        return float(font_size)

    @font_size.setter
    def font_size(self, size: float) -> None:
        self['fontSize'] = size

    @property
    def leading(self) -> float:
        leading = self['leading']
        assert isinstance(leading, float | int)
        return float(leading)

    @leading.setter
    def leading(self, leading: float) -> None:
        self['leading'] = leading

    @property
    def text_color(self) -> colors.Color:
        text_color = self['textColor']
        assert isinstance(text_color, colors.Color)
        return text_color

    @text_color.setter
    def text_color(self, color: colors.Color) -> None:
        self['textColor'] = color

    @property
    def subscripted(self) -> ParagraphStyle:
        try:
            return self._subscripted
        except AttributeError:
            self._subscripted = ParagraphStyle(
                name=f'{self.name}-subscripted',
                parent=self,
                font_size=self.sub_size,
                leading=self.leading - self.font_size
            )
            return self._subscripted

    @property
    def superscripted(self) -> ParagraphStyle:
        try:
            return self._superscripted
        except AttributeError:
            self._superscripted = ParagraphStyle(
                name=f'{self.name}-superscripted',
                parent=self,
                font_size=self.sup_size
            )
            return self._superscripted

    @property
    def bold(self) -> ParagraphStyle:
        if self.font_name[-1] == 'B':
            return self

        try:
            return self._bold
        except AttributeError:
            if len(self.font_name) >= 2 and self.font_name[-2:] == 'BI':
                font_name = self.font_name[0:-1]
            else:
                font_name = f'{self.font_name}B'
            self._bold = ParagraphStyle(
                name=f'{self.name}-bold',
                parent=self,
                font_name=font_name
            )
            return self._bold

    @property
    def italic(self) -> ParagraphStyle:
        if self.font_name[-1] == 'I':
            return self

        try:
            return self._italic
        except AttributeError:
            self._italic = ParagraphStyle(
                name=f'{self.name}-italic',
                parent=self,
                font_name=f'{self.font_name}I'
            )
            return self._italic

    @property
    def link(self) -> ParagraphStyle:
        try:
            return self._link
        except AttributeError:
            self._link = ParagraphStyle(
                name=f'{self.name}-link',
                parent=self,
                text_color=COLORS['Green'],
                linkUnderline=1,
                underlineWidth=0.25
            )
            return self._link


class TableStyle(_TableStyle):
    defaults_name_map = {
        'FONTNAME': 'font_name',
        'FACE': 'font_name',
        'FONTSIZE': 'font_size',
        'SIZE': 'font_size',
        'LEADING': 'leading',
        'TEXTCOLOR': 'color',
        'ALIGNMENT': 'alignment',
        'ALIGN': 'alignment',
        'LEFTPADDING': 'left_padding',
        'RIGHTPADDING': 'right_padding',
        'TOPPADDING': 'top_padding',
        'BOTTOMPADDING': 'bottom_padding',
        'BACKGROUND': 'background',
        'VALIGN': 'valign',
        'SPAN': 'span'
    }

    defaults = {
        'font_name': _DEF_FONT_NAME,
        'font_size': 10,
        'leading': 12,
        'left_padding': 6,
        'right_padding': 6,
        'top_padding': 3,
        'bottom_padding': 3,
        'first_line_indent': 0,
        'color': colors.black,
        'alignment': 'LEFT',
        'background': colors.white,
        'valign': 'BOTTOM',
        'span': None
    }

    def __init__(self,
                 name: str,
                 cmds: Any | None=None,
                 parent: Any | None=None,
                 **kwargs):
        _TableStyle.__init__(self, cmds, parent, **kwargs)
        self.name = name

    def is_within(self,
                  coords: tuple[int, int],
                  init_coords: tuple[int, int],
                  end_coords: tuple[int, int]
                 ) -> bool:
        x, y = coords
        init_x, init_y = init_coords
        end_x, end_y = end_coords

        if x < init_x or y < init_y:
            return False

        if end_x == -1:
            end_x = sys.maxsize

        if end_y == -1:
            end_y = sys.maxsize

        if x > end_x or y > end_y:
            return False

        return True

    def get_default(self, name: str) -> tuple | None:
        cmd_name = name.upper()
        def_name = self.defaults_name_map.get(cmd_name)
        if def_name is None:
            return None

        default = self.defaults.get(def_name)
        if default is None:
            return None

        return (cmd_name, (0, 0), (-1, -1), default)


    def get_styles(self,
                   name: str,
                   coords: tuple[int, int] | None=None
                  ) -> list:
        cmd_name = name.upper()
        cmds = [cmd for cmd in self.getCommands() if cmd[0] == cmd_name]
        if cmds == []:
            default = self.get_default(cmd_name)
            if default is None:
                return []
            return [default]

        if coords is None:
            return cmds

        coord_cmds = []
        for cmd in cmds:
            try:
                init_coords = cmd[1]
                end_coords = cmd[2]
            except IndexError:
                continue
            
            if self.is_within(coords, init_coords, end_coords):
                coord_cmds.append(cmd)

        if coord_cmds == []:
            default = self.get_default(cmd_name)
            if default is None:
                return []
            return [default]

        return coord_cmds

    def __get_stnd_style(self, name: str) -> Any | None:
        cmd_name = name.upper()
        cmds = self.get_styles(cmd_name)
        if cmds == []:
            def_name = self.defaults_name_map.get(cmd_name)
            if def_name is None:
                return None

            default = self.defaults.get(def_name)
            return default
        return cmds[0][3]

    @property
    def font_name(self) -> str:
        return self.__get_stnd_style('FONTNAME')

    @property
    def font_size(self) -> float:
        return self.__get_stnd_style('FONTSIZE')

    @property
    def leading(self) -> float:
        return self.__get_stnd_style('LEADING')

    @property
    def right_padding(self) -> float:
        return self.__get_stnd_style('RIGHTPADDING')

    @property
    def left_padding(self) -> float:
        return self.__get_stnd_style('LEFTPADDING')

    @property
    def top_padding(self) -> float:
        return self.__get_stnd_style('TOPPADDING')

    @property
    def bottom_padding(self) -> float:
        return self.__get_stnd_style('BOTTOMPADDING')

    @property
    def text_color(self) -> colors.Color:
        return self.__get_stnd_style('TEXTCOLOR')

    @property
    def alignment(self) -> str:
        return self.__get_stnd_style('ALIGNMENT')

    @property
    def background(self) -> colors.Color:
        return self.__get_stnd_style('BACKGROUND')

    @property
    def valign(self) -> str:
        return self.__get_stnd_style('VALIGN')

    def get_pstyle(self) -> ParagraphStyle:
        return ParagraphStyle(
            name=self.name,
            font_size=self.font_size,
            font_name=self.font_name
        )

    def add(self, cmd):
        self._cmds.append(cmd)


_T = TypeVar('_T', TableStyle, ParagraphStyle)


class StyleSheet(Generic[_T]):
    def __init__(self):
        self.styles: dict[str, _T] = {}

    def __getitem__(self, key: str) -> _T:
        return self.styles[key]

    def __setitem__(self, key: str, value: _T):
        self.styles[key] = value

    def add(self, style: _T, alias: str | None=None):
        self.styles[alias or style.name] = style
