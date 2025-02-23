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
    TSTYLES,
    DEF_PSTYLE,
    INNER_WIDTH
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
            style=TSTYLES["ElementLine"]
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
        space_after: float | None = None,
        space_before: float | None = None,
        indents: int = 0,
        indent_size: int = 0,
        **kwargs
    ) -> None:
        if kwargs.get("normalizedData", None) is not None:
            super().__init__(elements, **kwargs)
            return

        assert indents >= 0
        assert indent_size >= 0

        indents_width = indents * indent_size
        max_content_width = max_width - indents_width
        self._lines = [
            [ParagraphLine(line, measure)]
            for line
            in wrap_elements(elements, max_content_width)
        ]
        if self._lines == []:
            self._lines = [[]]

        row_heights: list[float] = []
        for line in self._lines:
            if line == []:
                row_heights.append(0.01)
            else:
                row_heights.append(line[0].height)

        self.total_height = math.fsum(row_heights)

        if indents == 0:
            col_widths = [max_content_width]
        else:
            col_widths = [indents_width, max_content_width]
            for line in self._lines:
                line.insert(0, "")

        if space_before is not None and space_before > 0:
            self._lines.insert(0, [""])
            row_heights.insert(0, space_before)

        if space_after is not None and space_after > 0:
            self._lines.append([""])
            row_heights.append(space_after)

        super().__init__(
            self._lines,
            colWidths=col_widths,
            rowHeights=row_heights,
            style=TSTYLES["ElementLine"],
            hAlign="LEFT"
        )

    def set_style(self, style: ParagraphStyle) -> None:
        for line in self._lines:
            for para_line in line:
                para_line.set_style(style)
