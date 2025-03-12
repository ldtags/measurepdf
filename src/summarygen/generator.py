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
    INNER_WIDTH,
    PSTYLES,
    TSTYLES,
    STYLES,
    NL_HEIGHT,
    DEFAULT_BULLET_INDENT_SIZE
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
        self.bullet_indent_size: int
        self.newline_height: float
        self.max_width: float
        self._is_bulleted: bool
        self._set_defaults()

    def _set_defaults(self) -> None:
        self.bullet_level = 0
        self.bullet_indent_size = DEFAULT_BULLET_INDENT_SIZE
        self.newline_height = NL_HEIGHT
        self.max_width = INNER_WIDTH
        self._is_bulleted = False

    def _join_sections(self, sections: list[HTMLSection]) -> list[HTMLSection]:
        """Joins as many adjacent HTML sections as possible and returns the
        joint sections.
        """

        if len(sections) <= 1:
            return sections

        html_sections: list[HTMLSection] = []
        cur_section = sections[0]
        for section in sections[1:]:
            if isinstance(cur_section, ParagraphSection) and cur_section.can_join(section):
                cur_section.join(section)
                continue

            if isinstance(section, ListSection):
                section.list_items = [self._join_sections(line) for line in section.list_items]

            html_sections.append(cur_section)
            cur_section = section

        html_sections.append(cur_section)
        return html_sections

    def handle_paragraph(self, section: ParagraphSection) -> SummaryParagraph:
        return SummaryParagraph(
            elements=section.elements,
            max_width=self.max_width,
            indent_level=section.indent_level,
            indent_size=section.indent_size,
            is_bulleted=self._is_bulleted,
            bullet_level=self.bullet_level,
            bullet_indent_size=self.bullet_indent_size
        )

    def handle_list(self, section: ListSection) -> list[Flowable]:
        flowables: list[Flowable] = []

        self.bullet_level += 1

        for item_sections in section.list_items:
            if item_sections == []:
                continue

            i = 0
            while i < len(item_sections) and isinstance(item_sections[i], NewlineSection):
                flowables.extend(self.convert_section(item_sections[i]))
                i += 1

            self._is_bulleted = True
            flowables.extend(self.convert_section(item_sections[i]))
            self._is_bulleted = False

            if len(item_sections) > i + 1:
                flowables.extend(self.convert_sections(item_sections[i + 1:]))

        self.bullet_level -= 1

        return flowables

    def handle_image(self, section: ImageSection) -> Table:
        indent_width = section.indent_level * section.indent_size
        bullet_indent_width = self.bullet_level * self.bullet_indent_size
        max_image_width = self.max_width - bullet_indent_width - indent_width
        max_image_width *= section.scale
        image = utils.get_image(section.img_path, max_width=max_image_width)
        data = [image]
        col_widths = [image.drawWidth]
        rem_space = max_image_width - image.drawWidth
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

        for _ in range(self.bullet_level):
            data.insert(0, "")
            col_widths.insert(0, self.bullet_indent_size)

        if self._is_bulleted and self.bullet_level != 0:
            data[self.bullet_level - 1] = XPreformatted(
                "<bullet>&bull</bullet> ",
                style=STYLES["Normal"]
            )

        for _ in range(section.indent_level):
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
            header_indexes=list(range(0, len(headers))),
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

    def handle_math(self, section: MathSection) -> Table:
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

    def convert_section(self, section: HTMLSection) -> list[Flowable]:
        """Converts an `HTMLSection` object into a `Flowable` object."""

        if isinstance(section, ParagraphSection):
            flowables = [self.handle_paragraph(section)]
        elif isinstance(section, ListSection):
            flowables = self.handle_list(section)
        elif isinstance(section, ImageSection):
            flowables = [self.handle_image(section)]
        elif isinstance(section, NewlineSection):
            flowables = [self.handle_newline()]
        elif isinstance(section, MathSection):
            flowables = [self.handle_math(section)]
        else:
            raise SummaryGenError(f"Unsupported HTML section type: {type(section)}")

        if section.space_before != 0:
            flowables.insert(0, Spacer(0.01, section.space_before))

        if section.space_after != 0:
            flowables.append(Spacer(0.01, section.space_after))

        return flowables

    def convert_sections(self, sections: list[HTMLSection]) -> list[Flowable]:
        """Converts multiple `HTMLSection` objects into a list of `Flowable`
        objects.
        """

        flowables: list[Flowable] = []
        for section in sections:
            flowables.extend(self.convert_section(section))

        return flowables

    def generate(
        self,
        sections: list[HTMLSection],
        newline_height: float | None = None,
        max_width: float | None = None,
        bullet_indent_size: int | None = None,
    ) -> list[Flowable]:
        logger.info("Generating flowables from HTML sections...")

        self.newline_height = newline_height or self.newline_height
        self.max_width = max_width or self.max_width
        self.bullet_indent_size = bullet_indent_size or self.bullet_indent_size

        sections = self._join_sections(sections)
        flowables = self.convert_sections(sections)

        self._set_defaults()

        logger.info(f"Flowables generated: {len(flowables)}")

        return flowables
