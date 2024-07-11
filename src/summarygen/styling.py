from __future__ import annotations
import os
import copy
from enum import Enum
from typing import Any, TypeVar, Generic, overload
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import TableStyle

from src import asset_path
from src.summarygen.types import _TABLE_SPAN


_U = TypeVar('_U')


PAGESIZE = letter
X_MARGIN = 0.45 * inch
Y_MARGIN = 1 * inch
INNER_WIDTH = PAGESIZE[0] - X_MARGIN * 2 - 12
INNER_HEIGHT = PAGESIZE[1] - Y_MARGIN * 2


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
        regular = self.register(FontType.Regular)
        bold = self.register(FontType.Bold)
        italic = self.register(FontType.Italic)
        bold_italic = self.register(FontType.BoldItalic)
        registerFontFamily(self.name,
                           normal=regular.fontName,
                           bold=bold.fontName,
                           italic=italic.fontName,
                           boldItalic=bold_italic.fontName)


__SourceSansPro = Font('SourceSansPro', 'source-sans-pro')
__SourceSansPro.register_family()
__SourceSansPro.register(FontType.Black, FontType.BlackItalic)

__Merriweather = Font('Merriweather', 'merriweather')
__Merriweather.register_family()
__Merriweather.register(FontType.Light, FontType.LightItalic)

__Helvetica = Font('Helvetica', 'helvetica')
__Helvetica.register_family()

__Arial = Font('Arial', 'arial')
__Arial.register_family()


def rgb_color(red: float, green: float, blue: float) -> colors.Color:
    return colors.Color(red=(red/255), green=(green/255), blue=(blue/255))


COLORS = {
    'ValueTableHeaderLight': rgb_color(174, 141, 100),
    'ValueTableHeaderDark': rgb_color(153, 121, 80),
    'ValueTableRowLight': rgb_color(242, 242, 242),
    'ValueTableRowAltLight': rgb_color(230, 230, 230),
    'ValueTableRowDark': rgb_color(230, 230, 230),
    'ValueTableRowAltDark': rgb_color(217, 217, 217),
    'ReferenceTagBG': rgb_color(100, 162, 68),
    'LightBrown': rgb_color(173, 140, 99),
    'DarkBrown': rgb_color(153, 121, 80),
    'Green': rgb_color(100, 163, 69)
}


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
                 text_color: colors.Color | None=None,
                 parent: BetterParagraphStyle | None=None,
                 x_padding: float=0,
                 y_padding: float=0,
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

        self.text_color = get_style_param('text_color',
                                          text_color,
                                          parent,
                                          colors.black)
        kwargs['textColor'] = self.text_color

        self.attrs = kwargs
        self.parent = parent
        super().__init__(name, parent, **kwargs)
        self.font_name = kwargs['fontName']
        self.font_size = kwargs['fontSize']
        self.leading = kwargs['leading']
        self.sup_size = kwargs['superscriptSize']
        self.sub_size = kwargs['subscriptSize']
        self.text_color = kwargs['textColor']
        self.x_padding = x_padding
        self.y_padding = y_padding

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

    @property
    def bold(self) -> BetterParagraphStyle:
        if self.font_name[-1] == 'B':
            return self

        try:
            return self._bold
        except AttributeError:
            if len(self.font_name) >= 2 and self.font_name[-2:] == 'BI':
                font_name = self.font_name[0:-1]
            else:
                font_name = f'{self.font_name}B'
            self._bold = BetterParagraphStyle(
                name=f'{self.name}-bold',
                parent=self,
                font_name=font_name
            )
            return self._bold

    @property
    def italic(self) -> BetterParagraphStyle:
        if self.font_name[-1] == 'I':
            return self

        try:
            return self._italic
        except AttributeError:
            self._italic = BetterParagraphStyle(
                name=f'{self.name}-italic',
                parent=self,
                font_name=f'{self.font_name}I'
            )
            return self._italic

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

    def set_font_size(self, size: float):
        self.set_attr('fontSize', size)
        self.font_size = size


class BetterTableStyle(TableStyle):
    def __init__(self,
                 name: str,
                 cmds: Any | None=None,
                 parent: Any | None=None,
                 **kwargs):
        super().__init__(cmds, parent, **kwargs)

        self.name = name
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

    def get_pstyle(self) -> BetterParagraphStyle:
        return BetterParagraphStyle(
            name=self.name,
            font_size=self.font_size,
            font_name=self.font_name
        )

    def add(self, cmd):
        self._cmds.append(cmd)


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


_DEF_FONT_SIZE = 10
_DEF_FONT_NAME = 'SourceSansPro'


def __gen_pstyles() -> StyleSheet[BetterParagraphStyle]:
    style_sheet = StyleSheet[BetterParagraphStyle]()
    style_sheet.add(
        BetterParagraphStyle(
            'Base',
            font_name=_DEF_FONT_NAME,
            font_size=_DEF_FONT_SIZE
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'SmallBase',
            font_name=_DEF_FONT_NAME,
            font_size=_DEF_FONT_SIZE - 1
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'SmallerBase',
            font_name=_DEF_FONT_NAME,
            font_size=_DEF_FONT_SIZE - 2
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'Paragraph',
            leading=14,
            parent=style_sheet['Base']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'SmallParagraph',
            font_size=_DEF_FONT_SIZE - 1,
            parent=style_sheet['Paragraph']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'SummaryTableItem',
            font_name='SourceSansPro',
            font_size=9
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'SummaryTableHeader',
            font_name='SourceSansProB',
            font_size=10
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'TitlePageSubtitle',
            font_name='SourceSansProB',
            font_size=17,
            text_color=COLORS['LightBrown']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'TitlePageTitle',
            font_name='MerriweatherL',
            font_size=34,
            leftIndent=2
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'TitleSectionTitle',
            font_name='SourceSansProB',
            font_size=10,
            text_color=COLORS['LightBrown']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'TitleSectionContent',
            font_name='SourceSansPro',
            font_size=12
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'Test',
            parent=style_sheet['Paragraph'],
            borderWidth=1,
            borderColor=colors.black
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'ReferenceTag',
            parent=style_sheet['Paragraph'].bold,
            text_color=colors.white,
            backColor=COLORS['ReferenceTagBG'],
            x_padding=5,
            y_padding=3
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'VTHeaderRefTag',
            parent=style_sheet['SmallerBase'].bold,
            text_color=colors.white,
            backColor=COLORS['Green'],
            x_padding=2.5,
            y_padding=1.5
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'ValueTableHeaderThin',
            text_color=colors.white,
            parent=style_sheet['SmallerBase']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'ValueTableHeader',
            font_name=f'{_DEF_FONT_NAME}B',
            parent=style_sheet['ValueTableHeaderThin']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'ValueTableDeterminant',
            parent=style_sheet['SmallBase']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'ValueTableItem',
            font_name=f'{_DEF_FONT_NAME}B',
            parent=style_sheet['SmallBase']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'TableHeader',
            font_name=f'{_DEF_FONT_NAME}B',
            font_size=_DEF_FONT_SIZE + 3.5
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'h2',
            font_name='Merriweather',
            font_size=19,
            keepWithNext=True
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'h3',
            font_name='SourceSansProB',
            font_size=18,
            spaceAfter=5
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'h6',
            font_name='Merriweather',
            font_size=11,
            spaceAfter=8
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'Link',
            font_name='SourceSansPro',
            leading=18.5,
            font_size=13.5,
            linkUnderline=1,
            underlineWidth=0.25,
            text_color=COLORS['Green']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'TitleLink',
            font_name='SourceSansPro',
            font_size=16,
            text_color=COLORS['Green']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'h6Link',
            linkUnderline=0,
            text_color=COLORS['Green'],
            parent=style_sheet['h6']
        )
    )
    style_sheet.add(
        BetterParagraphStyle(
            'BulletPoint',
            font_name='SourceSansPro',
            font_size=18
        )
    )

    return style_sheet


def __gen_tstyles() -> StyleSheet[BetterTableStyle]:
    style_sheet = StyleSheet[BetterTableStyle]()
    style_sheet.add(
        BetterTableStyle(
            'SummaryTable', 
            [
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('VALIGN', (0, 0), (1, -1), 'MIDDLE')
            ]
        )
    )
    style_sheet.add(
        BetterTableStyle(
            'SectionsTable',
            [
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('SPAN', (0, 0), (0, 2)),
                ('SPAN', (0, 3), (0, 6)),
                ('SPAN', (0, 7), (0, 9)),
                ('SPAN', (0, 10), (0, 13)),
                ('SPAN', (0, 14), (0, 17)),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (0, -1), 'TOP'),
                ('VALIGN', (1, 0), (1, -1), 'MIDDLE')
            ]
        )
    )
    style_sheet.add(
        BetterTableStyle(
            'ValueTable',
            [
                ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 9),
                ('RIGHTPADDING', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)
            ]
        )
    )
    style_sheet.add(
        BetterTableStyle(
            'ElementLine',
            [
                # ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]
        )
    )
    style_sheet.add(
        BetterTableStyle(
            'TitleSectionLeft',
            [
                ('ALIGN', (0, 0), (-1, -1), 'LEFT')
            ]
        )
    )
    style_sheet.add(
        BetterTableStyle(
            'TitleSectionRight',
            [
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT')
            ]
        )
    )
    style_sheet.add(
        BetterTableStyle(
            'TitleSectionContainer',
            [
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT')
            ]
        )
    )
    style_sheet.add(
        BetterTableStyle(
            'SummaryList',
            [
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (1, 0), (1, -1), -10),
                ('VALIGN', (1, 0), (1, -1), 'TOP')
            ]
        )
    )

    return style_sheet


STYLES = getSampleStyleSheet()
PSTYLES = __gen_pstyles()
TSTYLES = __gen_tstyles()


DEF_PSTYLE = PSTYLES['Paragraph']


def get_table_style(data: list[list],
                    headers: int=1,
                    determinants: int=0,
                    spans: list[_TABLE_SPAN]=[]
                   ) -> BetterTableStyle:
    table_style = copy.deepcopy(TSTYLES['ValueTable'])
    table_styles = table_style.getCommands()

    for i in range(0, headers):
        if determinants > 0:
            table_styles.append(('BACKGROUND',
                                 (0, i),
                                 (determinants - 1, i),
                                 COLORS['ValueTableHeaderLight']))
        if len(data) > 0 and len(data[0]) > determinants:
            table_styles.append(('BACKGROUND',
                                 (determinants, i),
                                 (-1, i),
                                 COLORS['ValueTableHeaderDark']))

    for i in range(headers, len(data)):
        if determinants > 0:
            if i % 2 == 1:
                color = COLORS['ValueTableRowLight']
            else:
                color = COLORS['ValueTableRowAltLight']
            table_styles.append(('BACKGROUND',
                                 (0, i),
                                 (determinants - 1, i),
                                 color))

        if len(data[i]) > determinants:
            if i % 2 == 1:
                color = COLORS['ValueTableRowDark']
            else:
                color = COLORS['ValueTableRowAltDark']
            table_styles.append(('BACKGROUND',
                                 (determinants, i),
                                 (-1, i),
                                 color))

    for span in spans:
        y, x = span[0]
        row_span, col_span = span[1]
        if col_span != 0:
            col_span -= 1
        if row_span != 0:
            row_span -= 1
        span_style = ('SPAN', (x, y), (x + col_span, y + row_span))
        table_styles.append(span_style)

    return BetterTableStyle(table_style.name, table_styles)
