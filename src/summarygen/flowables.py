from __future__ import annotations
import math
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
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES,
    INNER_WIDTH
)
from src.summarygen.rlobjects import BetterParagraphStyle
from src.exceptions import (
    WidthExceededError,
    ElementJoinError
)


NEWLINE = Spacer(1, 0.3 * inch)


class Reference(Paragraph):
    def __init__(self, text: str, link: str):
        ref_text = f'<link href=\"{link}\">{text.strip()}</link>'
        Paragraph.__init__(self, text=ref_text, style=PSTYLES['ReferenceTag'])


class ElementLine:
    def __init__(self,
                 elements: list[ParagraphElement] | None=None,
                 max_width: float | None=INNER_WIDTH):
        self.elements: list[ParagraphElement] = elements or []
        self.max_width = max_width
        self.widths: list[float] = [elem.width for elem in self.elements]
        self.heights: list[float] = [elem.height for elem in self.elements]
        if self.max_width != None and self.width > self.max_width:
            raise WidthExceededError(f'Max width of {self.max_width} exceeded')
        self.__index: int = 0

    @property
    def width(self) -> float:
        return math.fsum(self.widths)

    @property
    def height(self) -> float:
        return max(self.heights)

    def __getitem__(self, i: int) -> ParagraphElement:
        return self.elements[i]

    def __len__(self) -> int:
        return len(self.elements)

    def __iter__(self) -> ElementLine:
        return self

    def __next__(self) -> ParagraphElement:
        try:
            result = self.elements[self.__index]
        except IndexError:
            self.__index = 0
            raise StopIteration
        self.__index += 1
        return result

    def __add(self, element: ParagraphElement):
        if (self.max_width != None
                and element.width + self.width > self.max_width):
            raise WidthExceededError(f'Max width of {self.max_width} exceeded')

        try:
            self.elements[-1].join(element)
        except (IndexError, ElementJoinError):
            self.elements.append(element)

        self.widths.append(element.width)
        self.heights.append(element.height)

    def add(self, element: ParagraphElement):
        if element.text == '':
            return

        if self.elements == []:
            new_elem = element.copy(element.text.lstrip())
        else:
            new_elem = element

        if new_elem.type == ElemType.REF:
            self.__add(ParagraphElement(' ', type=ElemType.SPACE))
            self.__add(new_elem)
            self.__add(ParagraphElement(' ', type=ElemType.SPACE))
        else:
            self.__add(new_elem)

    def pop(self, index: int=-1) -> ParagraphElement:
        element = self.elements.pop(index)
        self.widths.pop(index)
        return element


class ParagraphLine(Table):
    def __init__(self,
                 element_line: ElementLine,
                 measure: Measure):
        self.element_line = element_line
        self.measure = measure
        self.ref_link = f'{self.measure.link}/#references_list'
        col_widths = [element.width for element in element_line]
        row_heights = [DEF_PSTYLE.leading]
        self.flowables = self.gen_flowables()
        Table.__init__(self,
                       [self.flowables],
                       colWidths=col_widths,
                       rowHeights=row_heights,
                       style=TSTYLES['ElementLine'])

    def gen_flowables(self) -> list[Flowable]:
        flowables: list[Flowable] = []
        for element in self.element_line:
            if element.type == ElemType.REF:
                text = f'<b>{element.text}</b>'
                flowables.append(Reference(text, self.ref_link))
            else:
                text = element.text
                if TextStyle.SUP in element.styles:
                    text = f'<super>{text}</super>'
                if TextStyle.SUB in element.styles:
                    text = f'<sub>{text}</sub>'
                if TextStyle.STRONG in element.styles:
                    text = f'<b>{text}</b>'
                if TextStyle.ITALIC in element.styles:
                    text = f'<i>{text}</i>'
                flowables.append(Paragraph(text, style=DEF_PSTYLE))
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
