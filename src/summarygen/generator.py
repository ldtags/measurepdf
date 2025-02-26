"""This module is used to generate reportlab flowables from the parsed
HTMLElement objects. Said objects can be parsed via the `parser` module.

The responsibility of this module is strictly flowable generation.
"""


import logging
from reportlab.pdfbase.pdfmetrics import stringWidth
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
    PSTYLES,
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
    NewlineSection,
    MathSection
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
        """Generates a `Flowable` that acts as a newline.

        Newline height is consistent and defined in the `generate` method.
        """

        return Spacer(0.01, self.newline_height)

    def _split_math(self, expression: str) -> list[str]:
        if expression == "":
            return [""]

        paren_count: int = 0
        tokens: list[str] = []
        cur_token: str = ""
        for i in range(len(expression)):
            char: str = expression[i]
            if char == " " and cur_token == "":
                continue

            cur_token += char
            if char == "(":
                paren_count += 1
            elif char == ")":
                paren_count -= 1

            if paren_count == 0:
                tokens.append(cur_token.strip())
                cur_token = ""

        if cur_token != "":
            tokens.append(cur_token.strip())

        return cur_token

    def handle_math(self, section: MathSection) -> Flowable:
        style = PSTYLES["Math"]
        max_width = stringWidth(section.expression, style.font_name, style.font_size)
        lines: list[tuple[Paragraph, float]] = [
            (
                Paragraph(
                    text=section.expression,
                    style=style
                ),
                max_width   
            )
        ]

        max_content_width = self.max_width - section.indent_level * section.indent_size
        while max_width > max_content_width:
            ok_lines: list[tuple[Paragraph, float]] = []
            problem_lines: list[tuple[str]] = []
            while lines != []:
                line, line_width = lines.pop()
                if line_width <= self.max_width:
                    ok_lines.append((line, line_width))
                else:
                    problem_lines.append(line.text)

            lines.extend(ok_lines)
            for line in problem_lines:
                new_lines = self._split_math(line)
                for new_line in new_lines:
                    lines.append((
                        Paragraph(
                            text=new_line,
                            style=style
                        ),
                        stringWidth(new_line, style.font_name, style.font_size)
                    ))

            max_width = 0
            for _, width in lines:
                max_width = max(max_width, width)

        content_width = max([line[1] for line in lines])
        data = [[line[0]] for line in lines]
        col_widths = [content_width]
        row_heights = [style.leading] * len(lines)
        if section.indent_level > 0:
            for _ in range(section.indent_level):
                for row in data:
                    row.insert(0, "")

                col_widths.insert(0, section.indent_size)

        rem_space = max_content_width - content_width
        match section.alignment:
            case Alignment.Center:
                for row in data:
                    row.insert(0, "")
                    row.append("")

                col_widths.insert(0, rem_space / 2)
                col_widths.append(rem_space / 2)
            case Alignment.Right:
                for row in data:
                    row.insert(0, "")

                col_widths.insert(0, rem_space)
            case _:
                pass

        if section.space_before > 0:
            data.insert(0, [""] * len(data[0]))
            row_heights.insert(0, section.space_before)

        if section.space_after > 0:
            data.append([""] * len(data[0]))
            row_heights.append(section.space_after)

        return Table(
            data=data,
            colWidths=col_widths,
            rowHeights=row_heights,
            style=TSTYLES["Unstyled"],
            hAlign=section.alignment.value.upper()
        )

    def convert_section(self, section: HTMLSection) -> Flowable:
        """Converts an `HTMLSection` object into a `Flowable` object."""

        if isinstance(section, ParagraphSection):
            return self.handle_paragraph(section)

        if isinstance(section, ListSection):
            return self.handle_list(section)

        if isinstance(section, ImageSection):
            return self.handle_image(section)

        if isinstance(section, NewlineSection):
            return self.handle_newline()

        if isinstance(section, MathSection):
            return self.handle_math(section)

        raise SummaryGenError(f"Unsupported HTML section type: {type(section)}")

    def convert_sections(self, sections: list[HTMLSection]) -> list[Flowable]:
        """Converts multiple `HTMLSection` objects into a list of `Flowable`
        objects.
        """

        return list(
            map(
                lambda section: self.convert_section(section),
                sections
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
