from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import inch, letter

from src.summarygen.rlobjects import (
    Font,
    BetterTableStyle,
    StyleSheet,
    BetterParagraphStyle
)


PAGESIZE = letter
X_MARGIN = 1 * inch
Y_MARGIN = 1 * inch
INNER_WIDTH = PAGESIZE[0] - X_MARGIN * 2
INNER_HEIGHT = PAGESIZE[1] - Y_MARGIN * 2


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
            ('TOPPADDING', (0, 0), (-1, -1), 8),
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
