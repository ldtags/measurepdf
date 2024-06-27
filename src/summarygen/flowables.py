from __future__ import annotations
from reportlab.lib.pagesizes import inch
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    Spacer,
    KeepTogether,
    XPreformatted
)

from src.etrm.models import Measure
from src.summarygen.models import (
    ParagraphElement,
    ElemType
)
from src.summarygen.styling import (
    BetterParagraphStyle,
    BetterTableStyle,
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES
)
from src.summarygen.rlobjects import ElementLine


_NL_HEIGHT = 0.3 * inch
NEWLINE = KeepTogether(Spacer(1, _NL_HEIGHT, isGlue=True))


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

    @property
    def line_matrix(self) -> list[list[Flowable]]:
        """Formats flowables so that the `Table` can read them
        
        Should only have one line within the outer array
        """

        return [self.flowables]

    def is_empty(self) -> bool:
        return self.element_line.elements == []


class TableCell(Table):
    def __init__(self,
                 elements: list[ParagraphLine],
                 width: float,
                 style: BetterParagraphStyle | None=None):
        self._elements = elements
        self.max_width = width
        self.pstyle = style
        if elements == []:
            elem_line = ElementLine([ParagraphElement('')], style=style)
            self.elements.append(ParagraphLine(elem_line))
        Table.__init__(self,
                       self.line_matrix,
                       colWidths=self.width,
                       rowHeights=self.row_heights,
                       style=TSTYLES['ElementLine'],
                       hAlign='LEFT')

    @property
    def elements(self) -> list[ParagraphLine]:
        lines: list[ParagraphLine] = []
        for para_line in self._elements:
            line = ElementLine(max_width=self.max_width)
            for elem in para_line.element_line:
                if elem.type == ElemType.NEWLINE:
                    lines.append(ParagraphLine(line))
                    line = ElementLine(max_width=self.max_width)
                else:
                    line.add(elem)
            if line.elements != []:
                lines.append(ParagraphLine(line))
            return lines

    @property
    def line_matrix(self) -> list[list[ParagraphLine]]:
        return [[elem] for elem in self.elements]

    @property
    def width(self) -> float:
        return max([line.width for line in self.elements])

    @property
    def row_heights(self) -> list[float]:
        return [elem.height for elem in self.elements]


class ValueTable(Table):
    def __init__(self,
                 elements: list[list[list[ElementLine]]],
                 style: BetterTableStyle,
                 col_widths: list[float],
                 row_heights: list[float],
                 measure: Measure):
        self.elements = elements
        self.col_widths = col_widths
        self.row_heights = row_heights
        self.measure = measure
        Table.__init__(self,
                       data=self.table_cells,
                       style=style,
                       colWidths=col_widths,
                       rowHeights=row_heights)

    @property
    def table_cells(self) -> list[list[TableCell]]:
        _table_cells: list[list[TableCell | str]] = []
        for frag_line in self.elements:
            cells: list[TableCell] = []
            for j, table_cell in enumerate(frag_line):
                if table_cell == []:
                    cell = ''
                else:
                    cell_lines: list[ParagraphLine] = []
                    for element_line in table_cell:
                        para_line = ParagraphLine(element_line=element_line,
                                                  measure=self.measure)
                        cell_lines.append(para_line)
                    cell = TableCell(cell_lines, width=self.col_widths[j])
                cells.append(cell)
            _table_cells.append(cells)
        return _table_cells

    @table_cells.setter
    def table_cells(self, _table_cells: list[list[TableCell]]):
        elements: list[list[list[ElementLine]]] = []
        for table_row in _table_cells:
            element_row: list[list[ElementLine]] = []
            for table_cell in table_row:
                element_row.append(
                    [para.element_line for para in table_cell.elements]
                )
            elements.append(element_row)
        self.elements = elements
