import math
from reportlab.platypus import (
    Table,
    Flowable,
    Paragraph,
    XPreformatted
)

from src.etrm.models import Measure
from src.summarygen.models.enums import (
    ElementType
)
from src.summarygen.styles import (
    ParagraphStyle,
    Alignment,
    TSTYLES,
    DEF_PSTYLE,
    INNER_WIDTH,
    DEFAULT_INDENT_SIZE,
    DEFAULT_BULLET_INDENT_SIZE,
    DEFAULT_ALIGNMENT
)
from src.summarygen.models import (
    ParagraphElement,
    ElementLine
)
from src.summarygen.flowables.utils import wrap_elements
from src.summarygen.flowables.general import Reference


class ParagraphLine(Table):
    """Conversion of an `ElementLine` to an inline `Flowable`."""

    def __init__(
        self,
        element_line: ElementLine,
        measure: Measure | None = None,
        **kwargs
    ) -> None:
        if kwargs.get("normalizedData", None) is not None:
            super().__init__(element_line, **kwargs)
            return

        self.element_line = element_line
        self.measure = measure
        if self.measure != None:
            self.ref_link = f"{self.measure.link}/#references_list"
        else:
            self.ref_link = ""

        self._cached_matrix = self.line_matrix
        super().__init__(
            self._cached_matrix,
            colWidths=self.col_widths,
            rowHeights=element_line.height,
            style=TSTYLES["Unstyled"]
        )

    @property
    def col_widths(self) -> list[float]:
        if self.is_empty():
            return [1]

        return [elem.width for elem in self.element_line]

    @property
    def width(self) -> float:
        _width = 0
        flowables = self.flowables
        for i, element in enumerate(self.element_line.elements):
            if element.type == ElementType.Reference:
                w, _ = flowables[i].wrap(0, 0)
                _width += w
            else:
                _width += element.width

        return _width

    @property
    def height(self) -> float:
        return self.element_line.height

    @property
    def flowables(self) -> list[Flowable]:
        if self.is_empty():
            return [Paragraph("", style=DEF_PSTYLE)]

        _flowables: list[Flowable] = []
        for element in self.element_line:
            if element.type == ElementType.Reference:
                _flowables.append(
                    Reference(
                        element.text,
                        style=element.style,
                        link=self.ref_link
                    )
                )
            else:
                _flowables.append(
                    XPreformatted(text=element.text_xml, style=element.style)
                )

        return _flowables

    @property
    def line_matrix(self) -> list[list[Flowable]]:
        """Formats flowables so that the `Table` can read them.
        
        Should only have one line within the outer array.
        """

        return [self.flowables]

    def is_empty(self) -> bool:
        return self.element_line.elements == []

    def set_style(self, style: ParagraphStyle) -> None:
        for flowable in self._cached_matrix:
            if isinstance(flowable, XPreformatted) or isinstance(flowable, Paragraph):
                flowable.style = style


class SummaryParagraph(Table):
    def __init__(
        self,
        elements: list[ParagraphElement],
        measure: Measure | None = None,
        max_width: float = INNER_WIDTH,
        indent_level: int = 0,
        indent_size: int = DEFAULT_INDENT_SIZE,
        is_bulleted: bool = False,
        bullet_level: int = 0,
        bullet_indent_size: int = DEFAULT_BULLET_INDENT_SIZE,
        h_align: Alignment = DEFAULT_ALIGNMENT,
        **kwargs
    ) -> None:
        if kwargs.get("normalizedData", None) is not None:
            super().__init__(elements, **kwargs)
            return

        assert max_width >= 0
        assert indent_level >= 0
        assert indent_size >= 0
        assert bullet_level >= 0
        assert bullet_indent_size >= 0

        indent_width = (indent_level + bullet_level) * indent_size
        if bullet_level != 0:
            indent_width += bullet_indent_size

        max_content_width = max_width - indent_width
        self._lines = [
            [ParagraphLine(line, measure)]
            for line
            in wrap_elements(elements, max_content_width)
        ]
        if self._lines == []:
            self._lines = [[ParagraphLine(ElementLine(""))]]

        row_heights: list[float] = []
        for line in self._lines:
            try:
                height = max([item.height for item in line])
            except ValueError:
                height = 0.01

            row_heights.append(height)

        content_width: float = 0.0
        for line in self._lines:
            try:
                line_width = math.fsum([
                    math.fsum(item.col_widths)
                    for item
                    in line
                ])
            except ValueError:
                line_width = 0.01

            content_width = max(content_width, line_width)

        col_widths: list[float] = [content_width]

        # apply indentation
        for _ in range(indent_level + bullet_level):
            col_widths.insert(0, indent_size)
            for line in self._lines:
                line.insert(0, "")

        # insert the bullet point if necessary
        if bullet_level != 0:
            col_widths.insert(-1, bullet_indent_size)
            for line in self._lines:
                line.insert(-1, "")

            if is_bulleted:
                self._lines[0][-2] = XPreformatted(
                    "<bullet>&bull</bullet> ",
                    DEF_PSTYLE
                )

        self.total_height = math.fsum(row_heights)
        super().__init__(
            self._lines,
            colWidths=col_widths,
            rowHeights=row_heights,
            style=TSTYLES["Unstyled"],
            hAlign=h_align.value.upper()
        )
