import copy
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from src.summarygen.types import _TableSpan
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


def _gen_pstyles() -> StyleSheet[ParagraphStyle]:
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
            "TableHeaderThin",
            text_color=colors.white,
            parent=style_sheet["SmallerBase"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TableHeader",
            font_name=f"{DEFAULT_FONT_NAME}B",
            parent=style_sheet["TableHeaderThin"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TableDeterminant",
            parent=style_sheet["SmallBase"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "TableItem",
            font_name=f"{DEFAULT_FONT_NAME}B",
            parent=style_sheet["SmallBase"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h1",
            font_name="Arial",
            font_size=14,
            space_before=18,
            space_after=12,
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
            font_name="Arial",
            font_size=12,
            space_before=8,
            space_after=8,
            text_color=COLORS["LightBlack"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h4",
            font_name="TimesNewRoman",
            font_size=11
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h5",
            font_name="AptosB",
            font_size=10
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "h6",
            font_name="AptosB",
            font_size=9
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
    style_sheet.add(
        ParagraphStyle(
            "IconCaption",
            font_name=DEFAULT_FONT_NAME,
            font_size=8,
            text_color=COLORS["LightBlack"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "VersionContainer",
            font_name=DEFAULT_FONT_NAME,
            font_size=12,
            text_color=colors.white
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "CoverCaption",
            font_name=DEFAULT_FONT_NAME,
            font_size=16,
            text_color=COLORS["LightBlack"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "CoverTitle",
            font_name=DEFAULT_FONT_NAME,
            font_size=18,
            text_color=COLORS["LightBlack"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "CoverPreDate",
            font_name=DEFAULT_FONT_NAME,
            font_size=DEFAULT_FONT_SIZE,
            text_color=COLORS["LightBlack"]
        )
    )
    style_sheet.add(
        ParagraphStyle(
            "CoverDate",
            font_name=DEFAULT_FONT_NAME,
            font_size=DEFAULT_FONT_SIZE,
            text_color=COLORS["Green"]
        )
    )

    return style_sheet


def _gen_tstyles() -> StyleSheet[TableStyle]:
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
            "TitleSectionLeft",
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "TitleSectionRight",
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "TitleSectionContainer",
            [
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "TitlePage",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (0, 0), "TOP"),
                ("VALIGN", (-1, -1), (-1, -1), "BOTTOM")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "SummaryList",
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0)
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
    style_sheet.add(
        TableStyle(
            "SunsettedMeasuresTable",
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["RevisionLogHeaderBG"]),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, COLORS["RevisionLogGridLine"]),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, COLORS["RevisionLogGridLine"]),
                ("VALIGN", (0, 1), (2, -1), "MIDDLE"),
                ("VALIGN", (3, 1), (3, -1), "TOP"),
                ("VALIGN", (4, 1), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (3, 0), "LEFT"),
                ("ALIGN", (4, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (2, -1), "LEFT"),
                ("ALIGN", (4, 1), (-1, -1), "CENTER")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "TOC",
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 2), (3, -1), "LEFT"),
                ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                ("ALIGN", (5, 0), (-1, 1), "CENTER"),
                ("SPAN", (5, 0), (-1, 0)),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("LINEABOVE", (0, 0), (-4, 0), 1, COLORS["RevisionLogGridLine"])
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "CoverCaption",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "CoverTopContent",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (-1, 0), (-1, 0), "TOP")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "CoverMidContent",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("SPAN", (0, 0), (-1, -1))
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "CoverDateContent",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (0, 0), "RIGHT")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "CoverBottomContent",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "CoverContent",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, 0), "TOP"),
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT")
            ]
        )
    )
    style_sheet.add(
        TableStyle(
            "PermutationsSummarySpreadsheet",
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (0, -1), "CENTER")
            ]
        )
    )

    return style_sheet


STYLES = getSampleStyleSheet()
PSTYLES = _gen_pstyles()
TSTYLES = _gen_tstyles()
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


def get_toc_style(
    uc_row_indices: list[int],
    generic_indices: list[int],
    res_indices: list[int],
    mfc_indices: list[int],
    nonres_indices: list[int]
) -> TableStyle:
    style = copy.deepcopy(TSTYLES["TOC"])
    cmds = style.getCommands()

    for y in uc_row_indices:
        cmds.append(("BACKGROUND", (0, y), (-4, y), COLORS["UseCategoryRowBG"]))
        cmds.append(("SPAN", (0, y), (3, y)))

    for y in generic_indices:
        cmds.append(("SPAN", (1, y), (-2, y)))

    for y in res_indices:
        cmds.append(("BACKGROUND", (5, y), (5, y), COLORS["ResGreen"]))

    for y in mfc_indices:
        cmds.append(("BACKGROUND", (6, y), (6, y), COLORS["MFCRed"]))

    for y in nonres_indices:
        cmds.append(("BACKGROUND", (7, y), (7, y), COLORS["NRBlue"]))

    return TableStyle(style.name, cmds)


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


def get_sunsetted_measures_table_style(
    num_rows: int,
    spans: list[_TableSpan],
    uc_row_indices: list[int]
) -> TableStyle:
    style = copy.deepcopy(TSTYLES["SunsettedMeasuresTable"])
    cmds = style.getCommands()
    line_color = COLORS["RevisionLogGridLine"]

    # apply use category row styles and styles relative to use category rows
    for i, y in enumerate(uc_row_indices):
        cmds.append(("BACKGROUND", (0, y), (-1, y), COLORS["UseCategoryRowBG"]))
        cmds.append(("SPAN", (0, y), (-1, y)))
        cmds.append(("ALIGN", (0, y), (-1, y), "CENTER"))
        if y != 1:
            cmds.append(("LINEABOVE", (0, y), (-1, y), 0.25, line_color))

        cmds.append(("LINEBELOW", (0, y), (-1, y), 0.25, line_color))

        if i != len(uc_row_indices) - 1:
            next_y = uc_row_indices[i + 1]
        else:
            next_y = -1

        # vertical line after the Start Date - End Date column
        cmds.append(("LINEAFTER", (3, y + 1), (3, next_y), 0.5, line_color))

    # get indices of each row that contains a spanned Start Date - End Date column
    sl_row_indice_map: dict[int, _TableSpan] = {}
    for span in spans:
        if span[1][0] == 0:
            continue

        start_y = span[0][0]
        for y in range(start_y, start_y + span[1][0]):
            sl_row_indice_map[y] = span

    # apply span-relative styles
    uc_row_indice_set = set(uc_row_indices)
    for y in range(num_rows):
        if y in uc_row_indice_set or y + 1 in uc_row_indice_set:
            continue

        if y not in sl_row_indice_map:
            cmds.append(("LINEBELOW", (1, y), (-1, y), 0.25, line_color))
            continue

        span = sl_row_indice_map[y]
        cmds.append(("LINEBELOW", (1, y), (2, y), 0.25, line_color))
        cmds.append(("LINEBELOW", (4, y), (-1, y), 0.25, line_color))
        if y == span[0][0] + span[1][0] - 1:
            cmds.append(("LINEBELOW", (3, y), (3, y), 0.25, line_color))

    return TableStyle(style.name, cmds)


def get_key_terminology_table_style(num_cols: int, col_size: int) -> TableStyle:
    style = copy.deepcopy(TSTYLES["KeyTerminologyTable"])
    cmds = style.getCommands()

    # add lines after each revision
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
    header_indexes: list[int] | set[int] | None = None,
    determinants: int = 0,
    spans: list[_TableSpan] = [],
    alternate_row_bg: bool = False,
) -> TableStyle:
    table_style = copy.deepcopy(TSTYLES["BasicTable"])
    cmds = table_style.getCommands()
    header_indexes = header_indexes or [0]
    if not isinstance(header_indexes, set):
        header_indexes = set(header_indexes)

    for y in header_indexes:
        # apply determinant header styles
        if determinants > 0:
            cmds.append((
                "BACKGROUND",
                (0, y),
                (determinants - 1, y),
                COLORS["TableHeaderLight"]
            ))

        # apply non-determinant header styles
        if len(data) > 0 and len(data[0]) > determinants:
            cmds.append((
                "BACKGROUND",
                (determinants, y),
                (-1, y),
                COLORS["TableHeaderDark"]
            ))

    # apply table body styles
    for y in range(len(data)):
        if y in header_indexes:
            continue

        row = data[y]
        for x in range(0, len(row)):
            if determinants > 0:
                if not alternate_row_bg or y % 2 == 1 or is_spanned(x, y, spans):
                    color = COLORS["TableRowLight"]
                else:
                    color = COLORS["TableRowAltLight"]

                cmds.append(("BACKGROUND", (x, y), (x, y), color))

            if len(row) > determinants:
                if y % 2 == 1 or is_spanned(x, y, spans):
                    color = COLORS["TableRowDark"]
                else:
                    color = COLORS["TableRowAltDark"]

                cmds.append(("BACKGROUND", (x, y), (x, y), color))

    # apply span styles
    for (y, x), (row_span, col_span) in spans:
        if col_span != 0:
            col_span -= 1

        if row_span != 0:
            row_span -= 1

        span_style = ("SPAN", (x, y), (x + col_span, y + row_span))
        cmds.append(span_style)

    return TableStyle(table_style.name, cmds)
