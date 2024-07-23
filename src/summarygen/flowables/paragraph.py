from reportlab.platypus import (
    Table,
    Flowable,
    Paragraph,
    XPreformatted
)

from src.etrm.models import Measure
from src.summarygen.styles import (
    TSTYLES,
    DEF_PSTYLE,
    INNER_WIDTH
)
from src.summarygen.rlobjects import (
    ParagraphElement,
    ElementLine,
    ElemType
)
from src.summarygen.flowables.utils import wrap_elements
from src.summarygen.flowables.general import Reference


class ParagraphLine(Table):
    """Conversion of an `ElementLine` to an inline `Flowable`."""

    def __init__(self,
                 element_line: ElementLine,
                 measure: Measure | None=None,
                 **kwargs):
        if kwargs.get('normalizedData', None) is not None:
            Table.__init__(self, element_line, **kwargs)
            return

        self.element_line = element_line
        self.measure = measure
        if self.measure != None:
            self.ref_link = f'{self.measure.link}/#references_list'
        else:
            self.ref_link = ''
        Table.__init__(self,
                       self.line_matrix,
                       colWidths=self.col_widths,
                       rowHeights=element_line.height,
                       style=TSTYLES['ElementLine'])

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
            if element.type == ElemType.REF:
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
            return [Paragraph('', style=DEF_PSTYLE)]

        _flowables: list[Flowable] = []
        for element in self.element_line:
            if element.type == ElemType.REF:
                _flowables.append(Reference(element.text,
                                            style=element.style,
                                            link=self.ref_link))
            else:
                _flowables.append(XPreformatted(text=element.text_xml,
                                                style=element.style))
        return _flowables

    @property
    def line_matrix(self) -> list[list[Flowable]]:
        """Formats flowables so that the `Table` can read them.
        
        Should only have one line within the outer array.
        """

        return [self.flowables]

    def is_empty(self) -> bool:
        return self.element_line.elements == []


class SummaryParagraph(Table):
    def __init__(self,
                 elements: list[ParagraphElement],
                 measure: Measure | None=None,
                 max_width: float=INNER_WIDTH,
                 space_after: float | None=None,
                 **kwargs):
        if kwargs.get('normalizedData', None) is not None:
            Table.__init__(self, elements, **kwargs)
            return

        lines = [[ParagraphLine(line, measure)]
                    for line in wrap_elements(elements, max_width)]
        if lines == []:
            lines = [[]]
        col_widths = [max_width]
        row_heights = [DEF_PSTYLE.leading] * len(lines)

        if space_after is not None:
            assert space_after > 0
            lines.append([''])
            row_heights.append(space_after)

        Table.__init__(self,
                       lines,
                       colWidths=col_widths,
                       rowHeights=row_heights,
                       style=TSTYLES['ElementLine'],
                       hAlign='LEFT')
