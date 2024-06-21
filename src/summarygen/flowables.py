from __future__ import annotations
from reportlab.lib.pagesizes import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    Spacer
)

from src.etrm.models import Measure
from src.summarygen.models import (
    ParagraphElement,
    ElemType,
    TextStyle
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
        ref_text = f'<link href=\"{link}\">{text.strip()}</link>'
        Paragraph.__init__(self, text=ref_text, style=PSTYLES['ReferenceTag'])


class ParagraphLine(Table):
    def __init__(self, element_line: ElementLine, measure: Measure):
        self.element_line = element_line
        self.measure = measure
        self.ref_link = f'{self.measure.link}/#references_list'
        col_widths = [element.width for element in element_line]
        row_heights = [DEF_PSTYLE.leading]
        Table.__init__(self,
                       [self.flowables],
                       colWidths=col_widths,
                       rowHeights=row_heights,
                       style=TSTYLES['ElementLine'])

    @property
    def flowables(self) -> list[Flowable]:
        flowables: list[Flowable] = []
        for element in self.element_line:
            if element.type == ElemType.REF:
                flowables.append(Reference(element.text_xml, self.ref_link))
            else:
                flowables.append(Paragraph(element.text_xml, style=element.style))
        return flowables


class ValueTableHeader(Paragraph):
    def __init__(self, text: str, link: str | None=None):
        header_text = text
        if link != None:
            header_text = f'<link href=\"{link}\">{header_text}</link>'
            style = PSTYLES['h6Link']
        else:
            style = PSTYLES['h6']
        Paragraph.__init__(self, header_text, style=style)


class TableCell(Table):
    def __init__(self,
                 elements: list[ParagraphElement],
                 max_width: float,
                 style: BetterParagraphStyle | None=None):
        self.elements = elements
        self.pstyle = style
        self.height = 0
        self.width = 0
        self.max_width = max_width
        self.col_widths: list[float] = []
        line = self.join_elements()
        Table.__init__(self,
                       [line],
                       colWidths=self.col_widths,
                       rowHeights=self.height,
                       style=TSTYLES['ElementLine'],
                       hAlign='LEFT')

    def element_style(self, element: ParagraphElement) -> BetterParagraphStyle:
        if element.type == ElemType.REF:
            return PSTYLES['ReferenceTag']
        elif self.pstyle != None:
            return self.pstyle
        elif (TextStyle.STRONG in element.styles
                and TextStyle.ITALIC in element.styles):
            return PSTYLES['ParagraphBoldItalic']
        elif TextStyle.STRONG in element.styles:
            return PSTYLES['ParagraphBold']
        elif TextStyle.ITALIC in element.styles:
            return PSTYLES['ParagraphItalic']
        else:
            return PSTYLES['Paragraph']

    def join_elements(self) -> list[Flowable]:
        self.height = 0
        self.width = 0
        self.col_widths = []
        line: list[Flowable] = []
        for element in self.elements:
            style = self.element_style(element)
            text = element.text
            font_size = style.font_size
            if TextStyle.SUB in element.styles:
                font_size = style.sub_size
                text = f'<sub>{text}</sub>'
            if TextStyle.SUP in element.styles:
                font_size = style.sup_size
                text = f'<super>{text}</super>'
            element_width = stringWidth(element.text,
                                        style.font_name,
                                        font_size)
            height = style.leading
            if element_width > self.max_width:
                scale = element_width // self.max_width
                element_width = self.max_width
                height *= scale + 1
                height += 6
            self.height = max(height, self.height)
            self.width += element_width
            self.col_widths.append(element_width)
            line.append(Paragraph(text, style=style))
        return line
