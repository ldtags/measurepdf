"""This module is used to generate reportlab flowables from the parsed
HTMLElement objects. Said objects can be parsed via the `parser` module.

The responsibility of this module is strictly flowable generation.
"""


import logging
import warnings
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    XPreformatted,
    Spacer
)

from src.summarygen import utils
from src.summarygen.styles import (
    Alignment,
    get_table_style,
    get_list_style,
    INNER_WIDTH,
    TSTYLES,
    STYLES,
    NL_HEIGHT
)
from src.summarygen.models import (
    HTMLSection,
    ParagraphSection,
    ListSection,
    TableSection,
    ImageSection,
    NewlineSection
)
from src.summarygen.flowables import SummaryParagraph
from src.summarygen.exceptions import SummaryGenError


logger = logging.getLogger(__name__)


class FlowableGenerator:
    def __init__(self) -> None:
        self.bullet_level: int
        self.newline_height: float
        self.max_width: float
        self._set_defaults()

    def _set_defaults(self) -> None:
        self.bullet_level = 0
        self.newline_height = NL_HEIGHT
        self.max_width = INNER_WIDTH

    def _join_sections(self, sections: list[HTMLSection]) -> list[HTMLSection]:
        """Joins as many adjacent HTML sections as possible and returns the
        joint sections.
        """

        if len(sections) <= 1:
            return sections

        html_sections: list[HTMLSection] = []
        cur_section = sections[0]
        for section in sections[1:]:
            if isinstance(cur_section, ParagraphSection) and type(section) == type(cur_section):
                cur_section.join(section)
            else:
                html_sections.append(cur_section)
                cur_section = section

        html_sections.append(cur_section)
        return html_sections

    def handle_paragraph(self, section: ParagraphSection) -> SummaryParagraph:
        return SummaryParagraph(
            elements=section.elements,
            max_width=self.max_width - section.indent_size * self.bullet_level,
            space_after=section.space_after,
            space_before=section.space_before,
            indents=section.indent_level,
            indent_size=section.indent_size
        )

    def handle_list(self, section: ListSection) -> Table:
        data: list[list[Flowable | str]] = []
        self.bullet_level += 1
        for list_item_sections in section.list_items:
            flowables = self.convert_sections(list_item_sections)
            if flowables == []:
                continue

            if isinstance(list_item_sections[0], ListSection):
                data.append(["", flowables[0]])
            else:
                data.append([
                    XPreformatted(
                        "<bullet>&bull</bullet> ",
                        style=STYLES["Normal"]
                    ),
                    flowables[0]
                ])

            if len(flowables) > 1:
                for flowable in flowables[1:]:
                    data.append(["", flowable])

        # Apply indentation
        self.bullet_level -= 1
        col_widths = [section.bullet_indent_size]
        bullet_index = self.bullet_level + section.indent_level + 1
        for _ in range(bullet_index):
            col_widths.append(section.bullet_indent_size)
            for row in data:
                row.insert(0, "")

        col_widths.append(self.max_width - sum(col_widths))
        row_heights: list[float] = []
        for row in data:
            flowable = row[-1]
            if isinstance(flowable, SummaryParagraph):
                row_heights.append(flowable.total_height)
            else:
                raise SummaryGenError(f"Cannot get height of flowable type: {type(flowable)}")

        list_flowable = Table(
            data,
            colWidths=col_widths,
            rowHeights=row_heights,
            hAlign="LEFT",
            style=get_list_style(bullet_index)
        )
        return Table(
            data=[[""], [list_flowable], [""]],
            colWidths=[sum(col_widths)],
            rowHeights=[section.space_before, sum(row_heights), section.space_after],
            hAlign="LEFT",
            style=TSTYLES["Unstyled"]
        )

    def handle_image(self, section: ImageSection) -> Table:
        max_width = (
            self.max_width
            - section.indent_level * section.indent_size
            - self.bullet_level * section.indent_size
        )
        image = utils.get_image(section.img_path, max_width=max_width)
        data = [image]
        col_widths = [image.drawWidth]
        rem_space = max_width - image.drawWidth
        match section.alignment:
            case Alignment.Left:
                data.append("")
                col_widths.append(rem_space)
            case Alignment.Center:
                data.append("")
                data.insert(0, "")
                col_widths.append(rem_space // 2)
                col_widths.insert(0, rem_space // 2)
            case Alignment.Right:
                data.insert(0, "")
                col_widths.insert(0, rem_space)

        if section.indent_level > 0:
            data.insert(0, "")
            col_widths.insert(0, section.indent_size)

        return Table(
            data=[data],
            colWidths=col_widths,
            rowHeights=[image.drawHeight],
            hAlign=section.alignment.value.upper(),
            style=TSTYLES["Unstyled"]
        )

    def _convert_table_cell(
        self,
        sections: list[HTMLSection] | None,
        max_width: float
    ) -> Flowable:
        if sections is None or sections == []:
            return Paragraph("")

        flowables: list[Flowable] = []
        for section in sections:
            flowables.append(self.convert_section(section))

        if len(flowables) == 1:
            return flowables[0]

        return Table(
            data=[[flowable] for flowable in flowables],
            colWidths=[max_width],
            style=TSTYLES["Unstyled"],
            hAlign="LEFT"
        )

    def _convert_table_rows(
        self,
        rows: list[list[list[HTMLSection] | None]],
        max_width: float
    ) -> list[list[Flowable]]:
        data: list[list[Flowable]] = []
        for row in rows:
            flowables: list[Flowable] = []
            for cell_sections in row:
                flowables.append(self._convert_table_cell(cell_sections, max_width))

            data.append(flowables)

        return data

    def handle_table(self, section: TableSection) -> Flowable:
        max_width = self.max_width - section.indent_level * section.indent_size
        headers = self._convert_table_rows(section.headers, max_width)
        rows = self._convert_table_rows(section.rows, max_width)
        data=[*headers, *rows]
        style = get_table_style(
            data=data,
            headers=len(headers),
            spans=section.spans
        )
        return Table(
            data=data,
            style=style,
            hAlign="LEFT"
        )

    def handle_newline(self) -> Flowable:
        return Spacer(0.01, self.newline_height)

    def convert_section(self, section: HTMLSection) -> Flowable | None:
        if isinstance(section, ParagraphSection):
            return self.handle_paragraph(section)

        if isinstance(section, ListSection):
            return self.handle_list(section)

        if isinstance(section, ImageSection):
            return self.handle_image(section)

        if isinstance(section, NewlineSection):
            return self.handle_newline()

        warnings.warn(f"Unsupported HTML section type: {type(section)}")
        return None

    def convert_sections(self, sections: list[HTMLSection]) -> list[Flowable]:
        return list(
            filter(
                lambda flowable: flowable is not None,
                map(
                    lambda section: self.convert_section(section),
                    sections
                )
            )
        )

    def generate(
        self,
        sections: list[HTMLSection],
        newline_height: float | None = None,
        max_width: float | None = None
    ) -> list[Flowable]:
        logger.info("Generating flowables from HTML sections...")

        self.newline_height = newline_height or self.newline_height
        self.max_width = max_width or self.max_width

        sections = self._join_sections(sections)
        flowables = self.convert_sections(sections)

        self._set_defaults()

        logger.info(f"Flowables generated: {len(flowables)}")

        return flowables
