import copy
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet

from src.summarygen.types import (
    _TableSpan,
    _TableOrient
)
from src.summarygen.styles.config import (
    DEFAULT_FONT_NAME,
    DEFAULT_FONT_SIZE
)
from src.summarygen.styles.colors import COLORS
from src.summarygen.styles.objects import (
    StyleSheet,
    ParagraphStyle,
    TableStyle
)


def __gen_pstyles() -> StyleSheet[ParagraphStyle]:
    style_sheet = StyleSheet[ParagraphStyle]()
    style_sheet.add(
        ParagraphStyle(
            "Base",
            font_name=DEFAULT_FONT_NAME,
            font_size=DEFAULT_FONT_SIZE
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "SmallBase",
            font_name=DEFAULT_FONT_NAME,
            font_size=DEFAULT_FONT_SIZE - 1
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "SmallerBase",
            font_name=DEFAULT_FONT_NAME,
            font_size=DEFAULT_FONT_SIZE - 2
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "Paragraph",
            leading=14,
            parent=style_sheet["Base"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "SmallParagraph",
            font_size=DEFAULT_FONT_SIZE - 1,
            parent=style_sheet["Paragraph"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TitlePageTitle",
            font_name="TimesNewRoman",
            font_size=32
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TitleSectionTitle",
            font_name="SourceSansProB",
            font_size=10,
            text_color=COLORS["LightBrown"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TitleSectionContent",
            font_name="SourceSansPro",
            font_size=12
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TitleLink",
            font_name="SourceSansPro",
            font_size=12,
            text_color=COLORS["Green"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "ReferenceTag",
            font_name=f"{DEFAULT_FONT_NAME}B",
            font_size=DEFAULT_FONT_SIZE - 3,
            text_color=colors.white,
            backColor=COLORS["ReferenceTagBG"],
            space_before=1,
            space_after=1
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "VTHeaderRefTag",
            parent=style_sheet["SmallerBase"].bold,
            text_color=colors.white,
            backColor=COLORS["Green"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "ValueTableHeaderThin",
            text_color=colors.white,
            parent=style_sheet["SmallerBase"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "ValueTableHeader",
            font_name=f"{DEFAULT_FONT_NAME}B",
            parent=style_sheet["ValueTableHeaderThin"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            'ValueTableDeterminant',
            parent=style_sheet['SmallBase']
        )
    )
    style_sheet.add(
        ParagraphStyle(
            'ValueTableItem',
            font_name=f'{DEFAULT_FONT_NAME}B',
            parent=style_sheet['SmallBase']
        )
    )
    style_sheet.add(
        ParagraphStyle(
            'TableHeader',
            font_name=f'{DEFAULT_FONT_NAME}B',
            font_size=DEFAULT_FONT_SIZE + 3.5
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h1",
            font_name="Arial",
            font_size=14,
            text_color=COLORS["h1"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h2",
            font_name="TimesNewRoman",
            font_size=17,
            space_after=8
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h3",
            font_name="TimesNewRoman",
            font_size=11
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h4",
            font_name="AptosB",
            font_size=10
        )
    )
    style_sheet.add(
        ParagraphStyle(
            'h6',
            font_name='Merriweather',
            font_size=11,
            space_after=8
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "BulletPoint",
            font_size=18
        )
    )
    style_sheet.add(
        ParagraphStyle(
            'TOCHeader',
            font_name='MerriweatherB',
            font_size=18,
            alignment=TA_CENTER
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TerminologyHeader",
            text_color=COLORS["LightBrown"],
            parent=style_sheet["Paragraph"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "Math",
            font_name="CambriaM",
            font_size=11
        )
    )

    return style_sheet


def __gen_tstyles() -> StyleSheet[TableStyle]:
    style_sheet = StyleSheet[TableStyle]()
    style_sheet.add(
        TableStyle(
            "BasicTable",
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "Unstyled",
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # ("GRID", (0, 0), (-1, -1), 1, colors.black)
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            'TitleSectionLeft',
            [
                ('ALIGN', (0, 0), (-1, -1), 'LEFT')
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            'TitleSectionRight',
            [
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT')
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            'TitleSectionContainer',
            [
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT')
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            'TitlePage',
            [
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('VALIGN', (0, 0), (0, 0), 'TOP'),
                ('VALIGN', (-1, -1), (-1, -1), 'BOTTOM')
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            'SummaryList',
            [
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0)
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "RevisionLog",
            [
                ("LINEABOVE", (0, 0), (-1, 0), 1, COLORS["RevisionLogGridLine"]),
                ("LINEABOVE", (0, 1), (-1, 1), 1, COLORS["RevisionLogGridLine"]),
                ("LINEBELOW", (0, -1), (-1, -1), 1, COLORS["RevisionLogGridLine"]),
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["RevisionLogHeaderBG"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "TOP")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "KeyTerminologyTable",
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["RevisionLogHeaderBG"]),
                ("LINEABOVE", (0, 0), (-1, 0), 1, COLORS["RevisionLogGridLine"]),
                ("LINEABOVE", (0, 1), (-1, 1), 1, COLORS["RevisionLogGridLine"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 1), (-1, -1), 1, COLORS["RevisionLogGridLine"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP")
            ]
        )
    )

    return style_sheet


STYLES = getSampleStyleSheet()
PSTYLES = __gen_pstyles()
TSTYLES = __gen_tstyles()
DEF_PSTYLE = PSTYLES["Paragraph"]


def is_spanned(x: int, y: int, spans: list[_TableSpan]) -> bool:
    for span in spans:
        y_min, x_min = span[0]
        y_inc, x_inc = span[1]
        y_max = y_min + y_inc - (1 if y_inc != 0 else 0)
        x_max = x_min + x_inc - (1 if x_inc != 0 else 0)
        if y >= y_min and x >= x_min and y <= y_max and x <= x_max:
            return True

    return False


def get_list_style(bullet_index: int) -> TableStyle:
    style = copy.deepcopy(TSTYLES["SummaryList"])
    cmds = style.getCommands()
    cmds.append((
        "VALIGN",
        (bullet_index, 0),
        (bullet_index, -1),
        "TOP"
    ))

    return TableStyle(style.name, cmds)


def get_kt_table_style(num_cols: int, col_size: int) -> TableStyle:
    style = copy.deepcopy(TSTYLES["KeyTerminologyTable"])
    cmds = style.getCommands()
    for i in range(num_cols - 1):
        cmds.append((
            "LINEAFTER",
            (i * col_size + 1, 0),
            (i * col_size + 1, -1),
            1,
            COLORS["RevisionLogGridLine"]
        ))

    return TableStyle(style.name, cmds)


def get_table_style(
    data: list[list],
    headers: int = 1,
    determinants: int = 0,
    spans: list[_TableSpan] = [],
    orient: _TableOrient = "top",
    alternate_row_bg: bool = False,
) -> TableStyle:
    table_style = copy.deepcopy(TSTYLES["BasicTable"])
    table_styles = table_style.getCommands()

    for i in range(0, headers):
        if determinants > 0:
            table_styles.append((
                'BACKGROUND',
                (0, i),
                (determinants - 1, i),
                COLORS['ValueTableHeaderLight']
            ))

        if len(data) > 0 and len(data[0]) > determinants:
            table_styles.append((
                'BACKGROUND',
                (determinants, i),
                (-1, i),
                COLORS['ValueTableHeaderDark']
            ))

    top_styles: list[tuple] = []
    left_styles: list[tuple] = []
    if determinants > 0:
        top_styles.append((
            'BACKGROUND',
            (0, 0),
            (determinants - 1, headers - 1),
            COLORS['ValueTableHeaderLight']
        ))
        left_styles.append((
            'BACKGROUND',
            (0, 0),
            (headers - 1, determinants - 1),
            COLORS['ValueTableHeaderLight']
        ))

    if len(data) > 0 and len(data[0]) > determinants:
        top_styles.append((
            'BACKGROUND',
            (determinants, 0),
            (-1, headers - 1),
            COLORS['ValueTableHeaderDark']
        ))
        left_styles.append((
            'BACKGROUND',
            (0, determinants),
            (headers - 1, -1),
            COLORS['ValueTableHeaderDark']
        ))

    for y in range(headers, len(data)):
        row = data[y]
        for x in range(0, len(row)):    # will cause a bug with left-orient tables
            if determinants > 0:
                if not alternate_row_bg or y % 2 == 1 or is_spanned(x, y, spans):
                    color = COLORS['ValueTableRowLight']
                else:
                    color = COLORS['ValueTableRowAltLight']

                top_styles.append((
                    'BACKGROUND',
                    (x, y),
                    (x, y),
                    color
                ))
                left_styles.append((
                    'BACKGROUND',
                    (y, x),
                    (y, x),
                    color
                ))

            if len(row) > determinants:
                if y % 2 == 1 or is_spanned(x, y, spans):
                    color = COLORS['ValueTableRowDark']
                else:
                    color = COLORS['ValueTableRowAltDark']

                top_styles.append((
                    'BACKGROUND',
                    (x, y),
                    (x, y),
                    color
                ))
                left_styles.append((
                    'BACKGROUND',
                    (y, x),
                    (y, x),
                    color
                ))

    if orient == 'left':
        table_styles.extend(left_styles)
    elif orient == 'top':
        table_styles.extend(top_styles)
    elif orient == 'top-left':
        table_styles.extend(top_styles)
        table_styles.extend(left_styles)

    for span in spans:
        y, x = span[0]
        row_span, col_span = span[1]
        if col_span != 0:
            col_span -= 1
        if row_span != 0:
            row_span -= 1
        span_style = ('SPAN', (x, y), (x + col_span, y + row_span))
        table_styles.append(span_style)

    return TableStyle(table_style.name, cmds=table_styles)
