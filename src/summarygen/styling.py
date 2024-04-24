import os
from typing import Any
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.platypus import TableStyle
from reportlab.lib import colors

from src import assets


def rgb_color(red: float, green: float, blue: float) -> colors.Color:
    return colors.Color(red=(red/255), green=(green/255), blue=(blue/255))


COLORS = {
    'ValueTableHeader': rgb_color(174, 141, 100),
    'ValueTableItemLight': rgb_color(242, 242, 242),
    'ValueTableItemDark': rgb_color(230, 230, 230)
}


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
        self.path = assets.get_path('fonts', font_dir)
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
        registerFontFamily(
            self.name,
            normal=self.name,
            bold=f'{self.name}B',
            italic=f'{self.name}I',
            boldItalic=f'{self.name}BI')


def register_fonts():
    Font('SourceSansPro', 'source-sans-pro').register()
    Font('Merriweather', 'merriweather').register()
    Font('Helvetica', 'helvetica').register()
    Font('Arial', 'arial').register()


class NamedTableStyle(TableStyle):
    def __init__(self,
                 name: str,
                 cmds: Any | None=None,
                 parent: Any | None=None,
                 **kwargs):
        self.name = name
        super().__init__(cmds, parent, **kwargs)


def gen_styles() -> StyleSheet1:
    register_fonts()
    style_sheet = StyleSheet1()
    style_sheet.add(
        ParagraphStyle('Paragraph',
                       fontName='SourceSansPro',
                       fontSize=13.5,
                       leading=13.5))
    style_sheet.add(
        ParagraphStyle('ParagraphBold',
                       fontName='SourceSansProB',
                       fontSize=13.5,
                       leading=13.5))
    style_sheet.add(
        ParagraphStyle('ReferenceTag',
                       fontName='SourceSansPro',
                       fontSize=13.5,
                       leading=13.5,
                       textColor=colors.white,
                       backColor=colors.green))
    style_sheet.add(
        ParagraphStyle('Header',
                       fontName='Merriweather',
                       leading=18,
                       fontSize=18,
                       spaceAfter=5))
    style_sheet.add(
        ParagraphStyle('TableHeader',
                       fontName='SourceSansProB',
                       leading=16.625,
                       fontSize=13.5))
    style_sheet.add(
        ParagraphStyle('h3',
                       fontName='SourceSansProB',
                       leading=15,
                       fontSize=15))
    style_sheet.add(
        ParagraphStyle('h6',
                       fontName='SourceSansPro',
                       leading=15,
                       fontSize=15))
    style_sheet.add(
        ParagraphStyle('Link',
                       fontName='SourceSansPro',
                       leading=18.5,
                       fontSize=13.5,
                       linkUnderline=1,
                       underlineWidth=0.25,
                       textColor=colors.green))

    style_sheet.add(
        NamedTableStyle('DetailsTable', [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 0.1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'SourceSansProB'),
            ('FONTNAME', (1, 0), (-1, -1), 'SourceSansPro'),
            ('FONTSIZE', (0, 0), (0, -1), 13.5),
            ('FONTSIZE', (1, 0), (-1, -1), 12)]))
    style_sheet.add(
        NamedTableStyle('ParametersTable', [
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'SourceSansPro'),
            ('FONTSIZE', (0, 0), (0, -1), 13.5),
            ('FONTSIZE', (1, 0), (-1, -1), 12)]))
    style_sheet.add(
        NamedTableStyle('SectionsTable', [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('SPAN', (0, 0), (0, 2)),
            ('SPAN', (0, 3), (0, 6)),
            ('SPAN', (0, 7), (0, 9)),
            ('SPAN', (0, 10), (0, 13)),
            ('SPAN', (0, 14), (0, 17)),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (0, -1), 'TOP'),
            ('VALIGN', (1, 0), (1, -1), 'MIDDLE')]))
    style_sheet.add(
        NamedTableStyle('ValueTable', [
            ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
            ('FONTNAME', (0, 0), (0, -1), 'ArialB'),
            ('FONTNAME', (1, 0), (-1, -1), 'Arial')]))

    return style_sheet


STYLES = gen_styles()


def value_table_style(data: list[list | tuple]) -> TableStyle:
    table_style: TableStyle = STYLES['ValueTable']
    table_styles = table_style.getCommands()
    for i, _ in enumerate(data):
        if i % 2 == 0:
            table_styles.append(('BACKGROUND',
                                (0, i),
                                (-1, i),
                                COLORS['ValueTableItemLight']))
        else:
            table_styles.append(('BACKGROUND',
                                 (0, i),
                                 (-1, i), COLORS['ValueTableItemDark']))
    return TableStyle(table_styles)


def embedded_table_style(data: list[list | tuple]) -> TableStyle:
    table_style: TableStyle = STYLES['ValueTable']
    table_styles = table_style.getCommands()
    for i, _ in enumerate(data):
        if i % 2 == 1:
            table_styles.append(('BACKGROUND',
                                 (0, i),
                                 (-1, i),
                                 COLORS['ValueTableItemLight']))
        else:
            table_styles.append(('BACKGROUND',
                                 (0, i),
                                 (-1, i),
                                 COLORS['ValueTableItemDark']))
    return TableStyle(table_styles)
