from __future__ import annotations
import os
from typing import Any, TypeVar, Generic
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import TableStyle

from src import asset_path


class Font:
    """Registerable font for the reportlab library
    
    Fonts must be stored in the `assets` directory as a directory named
    `asset_dir` that contains all font files

    Each font file must follow the name format `name`-`style`.ttf

    Supported (and required) font styles: `Regular`, `Bold`, `Italic`,
    `BoldItalic`

    Font styles are case specific
    """

    def __init__(self, name: str, font_dir: str):
        self.name = name
        self.path = asset_path(font_dir, 'fonts')
        self.regular = TTFont(
            f'{name}',
            os.path.join(self.path, f'{name}-Regular.ttf'))

        self.bold = TTFont(
            f'{name}B',
            os.path.join(self.path, f'{name}-Bold.ttf'))

        self.italic = TTFont(
            f'{name}I',
            os.path.join(self.path, f'{name}-Italic.ttf'))

        self.bold_italic = TTFont(
            f'{name}BI',
            os.path.join(self.path, f'{name}-BoldItalic.ttf'))

    def register(self):
        pdfmetrics.registerFont(self.regular)
        pdfmetrics.registerFont(self.bold)
        pdfmetrics.registerFont(self.italic)
        pdfmetrics.registerFont(self.bold_italic)
        registerFontFamily(self.name,
                           normal=self.name,
                           bold=f'{self.name}B',
                           italic=f'{self.name}I',
                           boldItalic=f'{self.name}BI')


def _rml_range(start: tuple[int, int], stop: tuple[int, int]) -> str:
    return f'start=\"{start[0]},{start[1]}\" stop=\"{stop[0]},{stop[1]}\"'


_U = TypeVar('_U')

def get_style_param(name: str,
                    param: _U | None,
                    parent: BetterParagraphStyle | None,
                    default: _U | None
                   ) -> _U:
    if param == None:
        try:
            return getattr(parent, name)
        except AttributeError:
            return default
    else:
        return param


class BetterParagraphStyle(ParagraphStyle):
    def __init__(self,
                 name: str,
                 font_name: str | None=None,
                 font_size: float | None=None,
                 leading: float | None=None,
                 sub_size: float | None=None,
                 sup_size: float | None=None,
                 parent: BetterParagraphStyle | None=None,
                 **kwargs):
        self.font_name = get_style_param('font_name',
                                         font_name,
                                         parent,
                                         'Helvetica')
        kwargs['fontName'] = self.font_name

        self.font_size = get_style_param('font_size',
                                         font_size,
                                         parent,
                                         12)
        kwargs['fontSize'] = self.font_size

        self.leading = get_style_param('leading',
                                       leading,
                                       parent,
                                       self.font_size * 1.2)
        kwargs['leading'] = self.leading

        self.sub_size = get_style_param('sub_size',
                                        sub_size,
                                        parent,
                                        self.font_size * (2 / 3))
        self.sup_size = get_style_param('sup_size',
                                        sup_size,
                                        parent,
                                        self.font_size * (2 / 3))
        self.attrs = kwargs
        self.parent = parent
        super().__init__(name, parent, **kwargs)

    def set_attr(self, name: str, value):
        self.attrs[name] = value
        self.parent._setKwds(**self.attrs)
        self.refresh()


class BetterTableStyle(TableStyle):
    def __init__(self,
                 name: str,
                 cmds: Any | None=None,
                 parent: Any | None=None,
                 **kwargs):
        super().__init__(cmds, parent, **kwargs)

        self.name = name
        self._rml_styles: list[str] = []
        self.font_size: float = 12
        self.font_name: str = 'Helvetica'
        self.top_padding: float = 6
        self.bottom_padding: float = 6
        self.left_padding: float = 6
        self.right_padding: float = 6
        for cmd in cmds:
            match cmd[0]:
                case 'FONTSIZE' | 'SIZE':
                    self.font_size = float(cmd[3])
                case 'FONTNAME':
                    self.font_name = str(cmd[3])
                case 'TOPPADDING':
                    self.top_padding = float(cmd[3])
                case 'BOTTOMPADDING':
                    self.bottom_padding = float(cmd[3])
                case 'LEFTPADDING':
                    self.left_padding = float(cmd[3])
                case 'RIGHTPADDING':
                    self.right_padding = float(cmd[3])

    def add(self, cmd):
        self._cmds.append(cmd)
        match cmd[0]:
            case 'FONTSIZE' | 'SIZE':
                self._rml_styles.append(
                    f'<blockFont size=\"{cmd[3]}\" '
                        + _rml_range(cmd[1], cmd[2])
                        + ' />')
            case 'FONTNAME' | 'NAME':
                self._rml_styles.append(
                    f'<blockFont name=\"{cmd[3]}\" '
                        + _rml_range(cmd[1], cmd[2])
                        + ' />')
            case 'BACKGROUND':
                color = cmd[3]
                if not isinstance(color, colors.Color):
                    raise Exception('color is required')
                self._rml_styles.append(
                    f'<blockBackground colorName=\"{color.hexval()}\" '
                        + _rml_range(cmd[1], cmd[2])
                        + ' />')
            case 'VALIGN':
                self._rml_styles.append(
                    f'<blockValign value=\"{cmd[3]}\" '
                        + _rml_range(cmd[1], cmd[2])
                        + ' />')
            case 'ALIGNMENT' | 'ALIGN':
                self._rml_styles.append(
                    f'<blockAlignment value=\"{cmd[3]}\" '
                        + _rml_range(cmd[1], cmd[2])
                        + ' />')
            case 'GRID':
                color = cmd[4]
                if not isinstance(color, colors.Color):
                    raise Exception('color is required')
                self._rml_styles.append(
                    f'<lineStyle kind=\"GRID\" thickness=\"{cmd[3]}\" '
                        + f'colorName=\"{color.hexval()}\" '
                        + _rml_range(cmd[1], cmd[2])
                        + ' />')

    @property
    def rml(self) -> str:
        return (f'<blockTableStyle id=\"{self.name}>\"'
                    + ''.join(self._rml_styles)
                    + '</blockTableStyle>')


_T = TypeVar('_T', BetterTableStyle, BetterParagraphStyle)

class StyleSheet(Generic[_T]):
    def __init__(self):
        self.styles: dict[str, _T] = {}

    def __getitem__(self, key: str) -> _T:
        return self.styles[key]

    def __setitem__(self, key: str, value: _T):
        self.styles[key] = value

    def add(self, style: _T, alias: str | None=None):
        self.styles[alias or style.name] = style

    @property
    def rml(self) -> str:
        rml_styles = ''
        for _, style in self.styles.items():
            rml_styles += style.rml
        return f'<stylesheet>{rml_styles}</stylesheet>'