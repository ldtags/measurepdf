from reportlab.lib import colors

from src.summarygen.rlobjects import (
    Font,
    BetterTableStyle,
    StyleSheet,
    BetterParagraphStyle
)


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
                             fontName='SourceSansPro',
                             fontSize=13.5,
                             leading=16.2))
    style_sheet.add(
        BetterParagraphStyle('SmallParagraph',
                             fontName='SourceSansPro',
                             fontSize=12,
                             leading=12))
    style_sheet.add(
        BetterParagraphStyle('ParagraphBold',
                             fontName='SourceSansProB',
                             fontSize=13.5,
                             leading=13.5))
    style_sheet.add(
        BetterParagraphStyle('ReferenceTag',
                             fontName='SourceSansPro',
                             fontSize=13.5,
                             leading=13.5,
                             textColor=colors.white,
                             backColor=COLORS['ReferenceTagBG']))
    style_sheet.add(
        BetterParagraphStyle('TableHeader',
                             fontName='SourceSansProB',
                             leading=16.625,
                             fontSize=13.5))
    style_sheet.add(
        BetterParagraphStyle('h2',
                             fontName='Merriweather',
                             leading=20.7,
                             fontSize=18,
                             spaceAfter=5))
    style_sheet.add(
        BetterParagraphStyle('h3',
                             fontName='SourceSansProB',
                             leading=15,
                             fontSize=15))
    style_sheet.add(
        BetterParagraphStyle('h6',
                             fontName='SourceSansPro',
                             leading=15,
                             fontSize=15))
    style_sheet.add(
        BetterParagraphStyle('Link',
                             fontName='SourceSansPro',
                             leading=18.5,
                             fontSize=13.5,
                             linkUnderline=1,
                             underlineWidth=0.25,
                             textColor=colors.green))

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
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (0, -1), 'TOP'),
            ('VALIGN', (1, 0), (1, -1), 'MIDDLE')]))
    style_sheet.add(
        BetterTableStyle('ValueTable', [
            ('GRID', (0, 0), (-1, -1), 0.25, colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))

    return style_sheet


PSTYLES = __gen_pstyles()
TSTYLES = __gen_tstyles()


def value_table_style(data: list[list | tuple],
                      embedded: bool=False
                     ) -> BetterTableStyle:
    table_style = TSTYLES['ValueTable']
    table_styles = table_style.getCommands()
    if embedded:
        switch = 1
        table_styles.extend([
            ('FONTNAME', (0, 0), (-1, -1), 'ArialB')
        ])
    else:
        switch = 0
        table_styles.extend([
            ('FONTNAME', (0, 0), (0, -1), 'ArialB'),
            ('FONTNAME', (1, 0), (-1, -1), 'Arial')])

    for i, _ in enumerate(data):
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
