from __future__ import annotations
import os
from typing import Any, TypeVar, Generic
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import inch, letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import TableStyle

from src import asset_path


_U = TypeVar('_U')


PAGESIZE = letter
X_MARGIN = 1 * inch
Y_MARGIN = 1 * inch
INNER_WIDTH = PAGESIZE[0] - X_MARGIN * 2
INNER_HEIGHT = PAGESIZE[1] - Y_MARGIN * 2


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
        kwargs['subscriptSize'] = self.sub_size

        self.sup_size = get_style_param('sup_size',
                                        sup_size,
                                        parent,
                                        self.font_size * (2 / 3))
        kwargs['superscriptSize'] = self.sup_size

        self.attrs = kwargs
        self.parent = parent
        super().__init__(name, parent, **kwargs)
        self.font_name = kwargs['fontName']
        self.font_size = kwargs['fontSize']
        self.leading = kwargs['leading']

    @property
    def subscripted(self) -> BetterParagraphStyle:
        try:
            return self._subscripted
        except AttributeError:
            self._subscripted = BetterParagraphStyle(
                name=f'{self.name}-subscripted',
                parent=self,
                font_size=self.sub_size,
                leading=self.leading - self.font_size
            )
            return self._subscripted

    @property
    def superscripted(self) -> BetterParagraphStyle:
        try:
            return self._superscripted
        except AttributeError:
            self._superscripted = BetterParagraphStyle(
                name=f'{self.name}-superscripted',
                parent=self,
                font_size=self.sup_size
            )
            return self._superscripted

    def refresh(self):
        try:
            del self._superscripted
        except AttributeError:
            pass

        try:
            del self._subscripted
        except AttributeError:
            pass

        super().refresh()

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


Font('SourceSansPro', 'source-sans-pro').register()
Font('Merriweather', 'merriweather').register()
Font('Helvetica', 'helvetica').register()
Font('Arial', 'arial').register()


def rgb_color(red: float, green: float, blue: float) -> colors.Color:
    return colors.Color(red=(red/255), green=(green/255), blue=(blue/255))

COLORS = {
    'ValueTableHeader': rgb_color(174, 141, 100),
    'ValueTableItemLight': rgb_color(242, 242, 242),
    'ValueTableItemDark': rgb_color(230, 230, 230),
    'ReferenceTagBG': rgb_color(100, 162, 68)
}


def __gen_pstyles() -> StyleSheet[BetterParagraphStyle]:
    style_sheet = StyleSheet[BetterParagraphStyle]()
    style_sheet.add(
        BetterParagraphStyle('Paragraph',
                             font_name='SourceSansPro',
                             font_size=13.5,
                             sub_size=8,
                             sup_size=8,
                             leading=16.2))
    style_sheet.add(
        BetterParagraphStyle('SmallParagraph',
                             font_size=12,
                             parent=style_sheet['Paragraph']))
    style_sheet.add(
        BetterParagraphStyle('Test',
                             parent=style_sheet['Paragraph'],
                             borderWidth=1,
                             borderColor=colors.black))
    style_sheet.add(
        BetterParagraphStyle('ParagraphBold',
                             font_name='SourceSansProB',
                             parent=style_sheet['Paragraph']))
    style_sheet.add(
        BetterParagraphStyle('ParagraphItalic',
                             font_name='SourceSansProI',
                             parent=style_sheet['Paragraph']))
    style_sheet.add(
        BetterParagraphStyle('ParagraphBoldItalic',
                             font_name='SourceSansProBI',
                             parent=style_sheet['Paragraph']))
    style_sheet.add(
        BetterParagraphStyle('ReferenceTag',
                             parent=style_sheet['ParagraphBold'],
                             textColor=colors.white,
                             backColor=COLORS['ReferenceTagBG'],
                             leading=13.5 * 1.2))
    style_sheet.add(
        BetterParagraphStyle('ValueTableHeader',
                             font_name='SourceSansProB',
                             parent=style_sheet['SmallParagraph'],
                             textColor=colors.white))
    style_sheet.add(
        BetterParagraphStyle('TableHeader',
                             font_name='SourceSansProB',
                             font_size=13.5))
    style_sheet.add(
        BetterParagraphStyle('h2',
                             font_name='Merriweather',
                             leading=20.7,
                             font_size=18,
                             spaceAfter=5))
    style_sheet.add(
        BetterParagraphStyle('h3',
                             font_name='SourceSansProB',
                             font_size=18,
                             spaceAfter=5))
    style_sheet.add(
        BetterParagraphStyle('h6',
                             font_name='Merriweather',
                             leading=15,
                             font_size=15,
                             spaceAfter=5))
    style_sheet.add(
        BetterParagraphStyle('Link',
                             font_name='SourceSansPro',
                             leading=18.5,
                             font_size=13.5,
                             linkUnderline=1,
                             underlineWidth=0.25,
                             textColor=colors.green))
    style_sheet.add(
        BetterParagraphStyle('h6Link',
                             linkUnderline=1,
                             underlineWidth=0.75,
                             textColor=colors.green,
                             parent=style_sheet['h6']))

    return style_sheet


def __gen_tstyles() -> StyleSheet[BetterTableStyle]:
    style_sheet = StyleSheet[BetterTableStyle]()
    style_sheet.add(
        BetterTableStyle('DetailsTable', [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 0.1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'SourceSansProB'),
            ('FONTNAME', (1, 0), (-1, -1), 'SourceSansPro'),
            ('FONTSIZE', (0, 0), (0, -1), 13.5),
            ('FONTSIZE', (1, 0), (-1, -1), 12)]))
    style_sheet.add(
        BetterTableStyle('ParametersTable', [
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('TOPPADDING', (0, 0), (0, -1), -1),
            ('TOPPADDING', (1, 0), (1, -1), 0.25),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'SourceSansPro'),
            ('FONTSIZE', (0, 0), (0, -1), 13.5),
            ('FONTSIZE', (1, 0), (-1, -1), 12)]))
    style_sheet.add(
        BetterTableStyle('SectionsTable', [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('SPAN', (0, 0), (0, 2)),
            ('SPAN', (0, 3), (0, 6)),
            ('SPAN', (0, 7), (0, 9)),
            ('SPAN', (0, 10), (0, 13)),
            ('SPAN', (0, 14), (0, 17)),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (0, -1), 'TOP'),
            ('VALIGN', (1, 0), (1, -1), 'MIDDLE')]))
    style_sheet.add(
        BetterTableStyle('ValueTable', [
            ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 9),
            ('RIGHTPADDING', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), COLORS['ValueTableHeader']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)]))
    style_sheet.add(
        BetterTableStyle('ElementLine', [
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

    return style_sheet


STYLES = getSampleStyleSheet()
PSTYLES = __gen_pstyles()
TSTYLES = __gen_tstyles()


DEF_PSTYLE = PSTYLES['Paragraph']


def value_table_style(data: list[list | tuple],
                      embedded: bool=False
                     ) -> BetterTableStyle:
    table_style = TSTYLES['ValueTable']
    table_styles = table_style.getCommands()
    if embedded:
        switch = 1
        table_styles.extend([
            ('FONTNAME', (0, 0), (-1, -1), 'ArialB')])
    else:
        switch = 0
        table_styles.extend([
            ('FONTNAME', (0, 0), (0, -1), 'ArialB'),
            ('FONTNAME', (1, 0), (-1, -1), 'Arial')])

    for i in range(1, len(data)):
        if i % 2 == switch:
            table_styles.append(('BACKGROUND',
                                (0, i),
                                (-1, i),
                                COLORS['ValueTableItemLight']))
        else:
            table_styles.append(('BACKGROUND',
                                 (0, i),
                                 (-1, i), COLORS['ValueTableItemDark']))

    return BetterTableStyle(table_style.name, table_styles)
