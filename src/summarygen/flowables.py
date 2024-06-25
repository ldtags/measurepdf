from __future__ import annotations
from reportlab.lib.pagesizes import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    Spacer,
    XPreformatted
)

from src.etrm.models import Measure
from src.summarygen.models import (
    ParagraphElement,
    ElemType
)
from src.summarygen.styling import (
    BetterParagraphStyle,
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES
)
from src.summarygen.rlobjects import ElementLine


NEWLINE = Spacer(1, 0.3 * inch)


class Reference(Paragraph):
    def __init__(self, text: str, link: str):
        ref_text = f'<link href=\"{link}\">{text}</link>'
        Paragraph.__init__(self, text=ref_text, style=PSTYLES['ReferenceTag'])


class ValueTableHeader(Paragraph):
    def __init__(self, text: str, link: str | None=None):
        header_text = text
        if link != None:
            header_text = f'<link href=\"{link}\">{header_text}</link>'
            style = PSTYLES['h6Link']
        else:
            style = PSTYLES['h6']
        Paragraph.__init__(self, header_text, style=style)


class ParagraphLine(Table):
    """Conversion of an `ElementLine` to an inline `Flowable`"""

    def __init__(self,
                 element_line: ElementLine,
                 measure: Measure | None=None):
        self.element_line = element_line
        self.measure = measure
        if self.measure != None:
            self.ref_link = f'{self.measure.link}/#references_list'
        else:
            self.ref_link = ''
        Table.__init__(self,
                       [self.flowables],
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
        return self.element_line.width

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
                _flowables.append(Reference(element.text_xml, self.ref_link))
            else:
                _flowables.append(XPreformatted(text=element.text_xml,
                                                style=element.style))
        return _flowables

    def is_empty(self) -> bool:
        return self.element_line.elements == []


class TableCell(Table):
    def __init__(self,
                 elements: list[ParagraphLine],
                 width: float,
                 style: BetterParagraphStyle | None=None):
        self.elements = elements
        self.pstyle = style
        if elements == []:
            elem_line = ElementLine([ParagraphElement('')], style=style)
            self.elements.append(ParagraphLine(elem_line))
        Table.__init__(self,
                       self.line_matrix,
                       colWidths=width,
                       rowHeights=self.row_heights,
                       style=TSTYLES['ElementLine'],
                       hAlign='LEFT')

    @property
    def line_matrix(self) -> list[list[ParagraphLine]]:
        return [[elem] for elem in self.elements]

    @property
    def row_heights(self) -> list[float]:
        return [elem.height for elem in self.elements]
