"""This module is used to parse HTML into objects that can be then used to
generate reportlab flowables.

The responsibility of this module is strictly the parsing and subsequent
conversion of HTML into `HTMLElement` objects. All flowable generation should
be handled in the `generator` module.

To add any specification as to how flowable generation should be handled,
update the HTMLElement sub-classes to include the desired specification. Then,
update the `generator` module to reflect those updates. This may require
creating entirely new HTMLElement sub-classes depending on the use-case.
"""


import copy
import logging
import warnings
from bs4 import BeautifulSoup, PageElement, NavigableString, Tag, ResultSet
from typing import Literal

from src.summarygen.types import _TableSpan
from src.summarygen.models import (
    HTMLSection,
    ParagraphElement,
    ParagraphSection,
    ListSection,
    ImageSection,
    TableSection,
    NewlineSection,
    MathSection,
    BulletOption,
    ElementType,
    TextStyle,
    CIRCLE_BULLET
)
from src.summarygen.styles import (
    ParagraphStyle,
    PSTYLES,
    DEF_PSTYLE,
    DEFAULT_INDENT_SIZE
)
from src.summarygen.constants import TAG_STYLE_MAP
from src.summarygen.exceptions import SummaryGenError


logger = logging.getLogger(__name__)


def _apply_spans(rows: list[ResultSet[Tag]]) -> list[ResultSet[Tag | None]]:
    content = copy.deepcopy(rows)
    for i, row in enumerate(rows):
        x_offset = 0
        for j, cell in enumerate(row):
            x = j + x_offset
            try:
                span_val = cell.get("colspan", 0)
                col_span = int(span_val)
            except ValueError:
                raise SummaryGenError(f"Invalid column span value: {span_val}")

            for _ in range(col_span - 1):
                content[i].insert(x + 1, None)
                x_offset += 1

            try:
                span_val = cell.get("rowspan", 0)
                row_span = int(span_val)
            except ValueError:
                raise SummaryGenError(f"Invalid row span value: {span_val}")

            for k in range(i + 1, i + row_span):
                try:
                    cur_row = content[k]
                except IndexError:
                    break

                if len(cur_row) < x + 1:
                    cur_row.extend([None] * (x - len(cur_row) + 1))
                else:
                    cur_row.insert(x, None)

    return content


def _get_table_contents(
    table: Tag,
    section: Literal["head", "body"]
) -> list[ResultSet[Tag | None]]:
    match section:
        case "head":
            section_tag = "thead"
            cell_tag = "th"
        case "body":
            section_tag = "tbody"
            cell_tag = "td"
        case other:
            raise SummaryGenError(f"Unexpected table section: {other}")

    row_elements: ResultSet[Tag] = []
    thead = table.find(section_tag)
    if isinstance(thead, Tag):
        row_elements = thead.find_all("tr")
    else:
        row_elements = table.find_all("tr")

    if row_elements == []:
        warnings.warn("No row elements found for HTML table section", RuntimeWarning)
        return []

    rows: list[ResultSet[Tag]] = []
    for row_element in row_elements:
        cell_elements: ResultSet[Tag] = row_element.find_all(cell_tag)
        if len(cell_elements) != 0:
            rows.append(cell_elements)

    return _apply_spans(rows)


def _get_spans(contents: list[ResultSet[Tag | None]]) -> list[_TableSpan]:
    spans: list[_TableSpan] = []
    for i, row in enumerate(contents):
        for j, cell in enumerate(row):
            if cell is None:
                continue

            try:
                span_val = cell.get("rowspan", 0)
                row_span = int(span_val)
            except ValueError:
                raise SummaryGenError(f"Invalid row span value: {span_val}")

            try:
                span_val = cell.get("colspan", 0)
                col_span = int(span_val)
            except ValueError:
                raise SummaryGenError(f"Invalid column span value: {span_val}")

            if row_span != 0 and col_span != 0:
                spans.append(((i, j), (row_span, col_span)))

    return spans


class HTMLParser:
    def __init__(self) -> None:
        self._indents: int
        self._indent_size: int
        self._bullet_indent_size: int
        self._bullet_option: BulletOption | None
        self._set_defaults()

    def _set_defaults(self) -> None:
        self._indents = 0
        self._indent_size = DEFAULT_INDENT_SIZE
        self._style = DEF_PSTYLE
        self._bullet_option = None

    def handle_text(self, element: NavigableString) -> ParagraphSection | NewlineSection:
        text = element.get_text()
        if text == "\n":
            return NewlineSection()

        return ParagraphSection(
            [ParagraphElement(text=text, style=self._style)],
            indent_level=self._indents,
            indent_size=self._indent_size
        )

    def handle_a(self, tag: Tag) -> ParagraphSection:
        """Simple <a> tag handler.

        Does not detect any styling within the <a> tag.

        Only supports URL linking and will not display linked images.
        """

        href = tag.get("href")
        text = tag.get_text()
        return ParagraphSection(
            [
                ParagraphElement(
                    text=text,
                    text_styles=[TextStyle.Link],
                    link=href,
                    style=self._style
                )
            ],
            indent_level=self._indents,
            indent_size=self._indent_size
        )

    def handle_styler(self, tag: Tag) -> list[ParagraphSection]:
        sections = self.convert_elements(tag.contents)
        style = TAG_STYLE_MAP.get(tag.name)
        if style is None:
            return sections

        for section in sections:
            if isinstance(section, ParagraphSection):
                section.add_style(style)

        return sections

    def handle_header(self, tag: Tag) -> ParagraphSection:
        return ParagraphSection(
            [ParagraphElement(text=tag.get_text(), style=PSTYLES[tag.name])],
            indent_level=self._indents,
            indent_size=self._indent_size
        )

    def _convert_rows(self, rows: list[ResultSet[Tag]]) -> list[list[list[HTMLSection] | None]]:
        row_sections: list[list[list[HTMLSection] | None]] = []
        for row_element in rows:
            row_section: list[list[HTMLSection]] = []
            for cell_element in row_element:
                if cell_element is None:
                    result = None
                else:
                    result = self.convert_element(cell_element)
                    if isinstance(result, HTMLSection):
                        result = [result]
    
                row_section.append(result)

            row_sections.append(row_sections)

        return row_sections

    def handle_table(self, tag: Tag) -> TableSection:
        header_row_elements = _get_table_contents(tag, "head")
        header_sections = self._convert_rows(header_row_elements)

        body_row_elements = _get_table_contents(tag, "body")
        body_sections = self._convert_rows(body_row_elements)

        return TableSection(
            body_sections,
            header_sections,
            spans=_get_spans([*header_row_elements, *body_row_elements]),
            indent_level=self._indents,
            indent_size=self._indent_size
        )

    def handle_th(self, tag: Tag) -> list[HTMLSection]:
        return self.convert_elements(tag.contents)

    def handle_td(self, tag: Tag) -> list[HTMLSection]:
        return self.convert_elements(tag.contents)

    def handle_ul(self, tag: Tag) -> ListSection:
        li_sections: list[list[HTMLSection]] = []
        li_elements: ResultSet[Tag] = tag.find_all("li", recursive=False)
        for li_element in li_elements:
            result = self.convert_element(li_element)
            if isinstance(result, HTMLSection):
                result = [result]

            li_sections.append(result)

        return ListSection(
            li_sections,
            bullet_option=self._bullet_option,
            indent_level=self._indents,
            indent_size=self._indent_size
        )

    def handle_li(self, tag: Tag) -> list[HTMLSection]:
        return self.convert_elements(tag.contents)

    def handle_img(self, tag: Tag) -> ImageSection:
        img_src = tag.get("src")
        return ImageSection(
            url=img_src,
            indent_level=self._indents,
            indent_size=self._indent_size
        )

    def handle_kth(self, tag: Tag) -> ParagraphSection:
        return ParagraphSection(
            [ParagraphElement(text=tag.get_text(), type=ElementType.TerminologyHeader)],
            indent_level=self._indents,
            indent_size=self._indent_size
        )

    def handle_math(self, tag: Tag) -> MathSection:
        return MathSection(
            expression=tag.get_text(),
            indent_level=self._indents,
            indent_size=self._indent_size,
            space_before=3,
            space_after=3
        )

    def handle_br(self) -> NewlineSection:
        return NewlineSection()

    def convert_element(self, element: PageElement) -> HTMLSection | list[HTMLSection]:
        if isinstance(element, NavigableString):
            return self.handle_text(element)

        if not isinstance(element, Tag):
            raise SummaryGenError(f"Unexpected page element type: {type(element)}")

        match element.name:
            case "div" | "span" | "p":
                return self.convert_elements(element.contents)
            case "a":
                return self.handle_a(element)
            case "em" | "strong" | "sup" | "sub" | "pre":
                return self.handle_styler(element)
            case "h3" | "h6":
                return self.handle_header(element)
            case "table":
                return self.handle_table(element)
            case "th":
                return self.handle_th(element)
            case "td":
                return self.handle_td(element)
            case "ul":
                return self.handle_ul(element)
            case "li":
                return self.handle_li(element)
            case "img":
                return self.handle_img(element)
            case "kth":
                return self.handle_kth(element)
            case "math":
                return self.handle_math(element)
            case "br":
                return self.handle_br()
            case other:
                raise SummaryGenError(f"Unsupported HTML tag: {other}")

    def convert_elements(self, elements: list[PageElement]) -> list[HTMLSection]:
        sections: list[HTMLSection] = []
        for element in elements:
            result = self.convert_element(element)
            if isinstance(result, HTMLSection):
                sections.append(result)
            elif isinstance(result, list):
                for section in result:
                    if not isinstance(section, HTMLSection):
                        raise SummaryGenError(f"Unknown HTML section type: {type(section)}")

                    sections.append(section)
            else:
                raise SummaryGenError(f"Unknown HTML section type: {type(result)}")

        return sections

    def parse(
        self,
        html: str,
        bullet_option: BulletOption = CIRCLE_BULLET,
        indents: int = 0,
        base_style: ParagraphStyle = DEF_PSTYLE
    ) -> list[HTMLSection]:
        """Converts HTML into HTML sections that can be converted into
        reportlab Flowables.
        """

        logger.info("Parsing HTML...")

        self._bullet_option = bullet_option
        self._indents = indents
        self._style = base_style

        soup = BeautifulSoup(html, "html.parser")
        sections = self.convert_elements(soup.contents)

        self._set_defaults()

        return sections
