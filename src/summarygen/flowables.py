from __future__ import annotations
import math
from typing import Literal
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    KeepTogether,
    XPreformatted,
    Spacer as _Spacer
)

from src import utils
from src.etrm.models import Measure, ValueTable as ValueTableObject
from src.summarygen.types import _TABLE_SPAN
from src.summarygen.models import (
    ParagraphElement,
    ElemType,
    VTObjectInfo
)
from src.summarygen.styling import (
    BetterParagraphStyle,
    BetterTableStyle,
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES,
    INNER_WIDTH,
    COLORS,
    get_table_style
)
from src.summarygen.rlobjects import ElementLine
from src.exceptions import WidthExceededError, SummaryGenError


class Spacer(_Spacer):
    def wrap(self, availWidth, availHeight):
        height = min(self.height, availHeight - 1e-8)
        return (availWidth, height)


_NL_HEIGHT = 0.3 * inch
NEWLINE = Spacer(1, _NL_HEIGHT, isGlue=True)


class TableBaseClass(Table):
    """Handler for the extra `Table` constructor call made during the
    reportlab build process

    Use the `CustomTable` class for creating custom `Table` flowables
    """

    def __init__(self, data: list[list | tuple], **kwargs):
        Table.__init__(self, data, **kwargs)


class CustomTable(TableBaseClass):
    """Custom flowable class for extending the reportlab `Table` class"""

    def __init__(self,
                 data: list[list | tuple],
                 col_widths: list[float] | float | None=None,
                 row_heights: list[float] | float | None=None,
                 style: BetterTableStyle | None=None,
                 **kwargs):
        if kwargs.get('normalizedData', None) is not None:
            TableBaseClass.__init__(self, data, **kwargs)
            return

        if data == []:
            data = [[]]

        if col_widths is not None:
            if isinstance(col_widths, float | int):
                col_widths = [col_widths]

            for row in data:
                assert len(col_widths) == len(row)
                for cell in row:
                    assert cell != 0

        if row_heights is not None:
            if isinstance(row_heights, float | int):
                row_heights = [row_heights]
            
            for column in [list(col) for col in zip(*data)]:
                assert len(row_heights) == len(column)
                for cell in column:
                    assert cell != 0

        TableBaseClass.__init__(self,
                                data=data,
                                colWidths=col_widths,
                                rowHeights=row_heights,
                                style=style,
                                **kwargs)


class TitleSection(Flowable):
    def __init__(self,
                 title: str,
                 content: str | None=None,
                 side: Literal['left', 'right']='left'):
        self.title = title
        self.content = content
        self.side = side
        self.indent = 7
        self.rect_width = 3.5

    def wrap(self, *args) -> tuple[float, float]:
        title_style = PSTYLES['TitleSectionTitle']
        title_width = stringWidth(self.title,
                                  title_style.font_name,
                                  title_style.font_size)
        offset = title_style.leading - title_style.font_size
        height = title_style.leading + offset * 2

        if self.content is not None:
            content_style = PSTYLES['TitleSectionContent']
            content_width = stringWidth(self.content,
                                        content_style.font_name,
                                        content_style.font_size)
            offset = content_style.leading - content_style.font_size
            height += content_style.leading + offset * 2
        else:
            content_width = 0

        text_width = max(title_width, content_width)
        width = text_width + self.indent + self.rect_width
        return (width, height)

    def __draw_rectangle(self, width: float, height: float):
        canvas = self.canv
        if not isinstance(canvas, Canvas):
            return

        canvas.saveState()
        try:
            if self.side == 'left':
                x = 0
            else:
                x = width - self.rect_width
            canvas.setFillColor(COLORS['LightBrown'])
            canvas.rect(x=x,
                        y=0,
                        width=self.rect_width,
                        height=height,
                        stroke=0,
                        fill=1)
        finally:
            canvas.restoreState()

    def __draw_text(self, width: float, height: float):
        canvas = self.canv
        if not isinstance(canvas, Canvas):
            return
        
        canvas.saveState()
        try:
            title_style = PSTYLES['TitleSectionTitle']
            if self.side == 'left':
                x = self.rect_width + self.indent
            else:
                title_width = stringWidth(self.title,
                                          title_style.font_name,
                                          title_style.font_size)
                x = width - self.rect_width - self.indent - title_width
            y = height - title_style.leading
            text_obj = canvas.beginText(x=x, y=y)
            text_obj.setFillColor(title_style.text_color)
            text_obj.setFont(title_style.font_name,
                             title_style.font_size,
                             title_style.leading)
            text_obj.textOut(self.title)
            canvas.drawText(text_obj)

            if self.content is not None:
                canvas.restoreState()
                canvas.saveState()
                content_style = PSTYLES['TitleSectionContent']
                if self.side == 'left':
                    x = self.rect_width + self.indent
                else:
                    content_width = stringWidth(self.content,
                                                content_style.font_name,
                                                content_style.font_size)
                    offset = self.rect_width + self.indent
                    x = width - offset - content_width
                y -= content_style.leading + 4
                text_obj = canvas.beginText(x=x, y=y)
                text_obj.setFont(content_style.font_name,
                                 content_style.font_size,
                                 content_style.leading)
                text_obj.textOut(self.content)
                canvas.drawText(text_obj)
        finally:
            canvas.restoreState()

    def draw(self):
        w, h = self.wrap()
        if self.side == 'left':
            self.__draw_rectangle(w, h)
            self.__draw_text(w, h)
        else:
            self.__draw_text(w, h)
            self.__draw_rectangle(w, h)


class TitleSectionSubContainer(CustomTable):
    def __init__(self,
                 sections: list[TitleSection],
                 side: Literal['left', 'right']='left',
                 **kwargs):
        col_widths: list[float] = []
        row_heights: list[float] = []
        for section in sections:
            width, height = section.wrap()
            col_widths.append(width)
            row_heights.append(height)
        offset_cells = [''] * len(sections)
        offset_heights = [25] * len(sections)
        sections_zip = zip(sections, offset_cells)
        heights_zip = zip(row_heights, offset_heights)
        _sections = [item for pair in sections_zip for item in pair]
        _heights = [item for pair in heights_zip for item in pair]
        if side == 'left':
            style = TSTYLES['TitleSectionLeft']
        else:
            style = TSTYLES['TitleSectionRight']
        CustomTable.__init__(self,
                             [[section] for section in _sections],
                             col_widths=max(col_widths),
                             row_heights=_heights,
                             style=style,
                             hAlign='left',
                             **kwargs)


class TitleSectionContainer(CustomTable):
    def __init__(self, sections: list[list[TitleSection]], **kwargs):
        if len(sections) != 2:
            raise SummaryGenError('Cannot generate a title section container'
                                  f' with {len(sections)} column(s)')

        left_container = TitleSectionSubContainer(sections[0], 'left')
        right_container = TitleSectionSubContainer(sections[1], 'right')
        CustomTable.__init__(self,
                             [[left_container, right_container]],
                             col_widths=[INNER_WIDTH / 2] * 2,
                             style=TSTYLES['TitleSectionContainer'],
                             **kwargs)


class Reference(Flowable):
    def __init__(self,
                 text: str,
                 link: str | None=None,
                 x_padding: float=5,
                 y_padding: float=2):
        self.text = text
        self.link = link
        self.x_padding = x_padding
        self.y_padding = y_padding
        self.base_style = PSTYLES['ReferenceTag']
        self.style = self.base_style.superscripted
        text_width =  stringWidth(self.text,
                                  self.style.font_name,
                                  self.style.font_size)
        self.__width = text_width + self.x_padding
        self.__height = self.base_style.font_size + self.y_padding

    def wrap(self, *args) -> tuple[float, float]:
        return (self.__width, self.__height)

    def draw(self):
        canvas = self.canv
        if not isinstance(canvas, Canvas):
            return

        bg_color = COLORS['ReferenceTagBG']
        y = self.__height - self.style.font_size - self.y_padding

        canvas.saveState()
        try:
            canvas.setFillColor(bg_color)

            tri_path = canvas.beginPath()
            tri_path.moveTo(x=0, y=y)
            tri_path.lineTo(x=self.__width / 2, y=y)
            tri_path.lineTo(x=self.__width / 4, y=0)
            canvas.drawPath(tri_path, stroke=0, fill=1)

            canvas.rect(x=0,
                        y=y,
                        width=self.__width,
                        height=self.style.font_size + self.y_padding,
                        stroke=0,
                        fill=1)

            canvas.restoreState()
            canvas.saveState()

            text_obj = canvas.beginText(x=self.x_padding / 2,
                                        y=y + 1.5 + self.y_padding / 2)
            text_obj.setFont(self.style.font_name,
                             self.style.font_size,
                             self.style.leading)
            text_obj.setFillColor(self.style.text_color)
            text_obj.textOut(self.text)
            canvas.drawText(text_obj)

            if self.link is not None:
                area = (0,
                        0,
                        self.__width - self.x_padding / 2,
                        self.__height)
                canvas.linkURL(url=self.link,
                               rect=area,
                               relative=1)
        finally:
            canvas.restoreState()


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
                _flowables.append(Reference(element.text, self.ref_link))
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


def split_word(element: ParagraphElement,
               rem_width: float=INNER_WIDTH,
               max_width: float=INNER_WIDTH
              ) -> list[ParagraphElement]:
    if element.text == 'Refrigerator':
        pass
    width = rem_width
    word: str = element.text
    frags: list[ParagraphElement] = []
    i = 0
    while i < len(word):
        j = i + 1
        elem_frag = element.copy(text=word[i:j])
        while j < len(word) and elem_frag.width < width:
            j += 1
            elem_frag = element.copy(text=word[i:j])

        if j == len(word) and elem_frag.width < width:
            frags.append(elem_frag)
            break

        frags.append(element.copy(text=word[i:j - 1]))
        i = j - 1
        width = max_width
    return frags


def wrap_elements(elements: list[ParagraphElement],
                  max_width: float=INNER_WIDTH,
                  style: BetterParagraphStyle | None=None
                 ) -> list[ElementLine]:
    element_lines: list[ElementLine] = []
    current_line = ElementLine(max_width=max_width, style=style)
    for element in elements:
        try:
            current_line.add(element)
        except WidthExceededError:
            for elem in element.split():
                try:
                    current_line.add(elem)
                except WidthExceededError:
                    if elem.width > max_width:
                        avail_width = max_width - current_line.width
                        word_frags = split_word(elem, avail_width, max_width)
                        current_line.add(word_frags[0])
                        element_lines.append(current_line)
                        if len(word_frags) > 1:
                            for word_frag in word_frags[1:len(word_frags)]:
                                current_line = ElementLine(max_width=max_width,
                                                           style=style)
                                current_line.add(word_frag)
                        else:
                            current_line = ElementLine(max_width=max_width,
                                                       style=style)
                    else:
                        element_lines.append(current_line)
                        current_line = ElementLine(max_width=max_width,
                                                   style=style)
                        current_line.add(elem)
    if len(current_line) != 0:
        element_lines.append(current_line)
    return element_lines


class SummaryParagraph(Table):
    def __init__(self,
                 elements: list[ParagraphElement],
                 measure: Measure | None=None,
                 **kwargs):
        if kwargs != {}:
            Table.__init__(self, elements, **kwargs)
            return

        lines = [[ParagraphLine(line, measure)]
                    for line in wrap_elements(elements)]
        if lines == []:
            lines = [[]]
        col_widths = [INNER_WIDTH]
        row_heights = [DEF_PSTYLE.leading] * len(lines)
        Table.__init__(self,
                       lines,
                       colWidths=col_widths,
                       rowHeights=row_heights,
                       style=TSTYLES['ElementLine'],
                       hAlign='LEFT')


class SummaryTable(CustomTable):
    def __init__(self,
                 elements: list[list[str]],
                 header_orient: Literal['top', 'left']='top',
                 header_style: BetterParagraphStyle=PSTYLES['TableHeader'],
                 body_style: BetterParagraphStyle=PSTYLES['Paragraph'],
                 table_style: BetterTableStyle=TSTYLES['SummaryTable'],
                 col_widths: list[float] | None=None):
        """Custom flowable for tables that are directly placed onto
        the summary PDF
        """

        self.table_style = table_style
        self.table_width = INNER_WIDTH

        if len(elements) > 1:
            row_len = len(elements[0])
            for row in elements[1:]:
                if len(row) != row_len:
                    raise SummaryGenError('All summary table rows must have'
                                          ' the same length')
                if col_widths is not None and len(row) != len(col_widths):
                    raise SummaryGenError('Incorrect amount of column widths:'
                                          f' got {len(col_widths)}, but',
                                          f' expected {len(row)}')

        self.style_matrix: list[list[BetterParagraphStyle]] = []
        data: list[list[Paragraph]] = []
        for y, row in enumerate(elements):
            style_row: list[BetterParagraphStyle] = []
            data_row: list[Paragraph] = []
            for x, cell in enumerate(row):
                if (y == 0 and header_orient == 'top'
                        or x == 0 and header_orient == 'left'):
                    style = header_style
                else:
                    style = body_style
                style_row.append(style)
                data_row.append(Paragraph(cell, style=style))
            self.style_matrix.append(style_row)
            data.append(data_row)

        col_widths = col_widths or self.__calc_col_widths(data)
        row_heights = self.__calc_row_heights(data, col_widths)
        CustomTable.__init__(self,
                             data=data,
                             col_widths=col_widths,
                             row_heights=row_heights,
                             style=table_style,
                             hAlign='LEFT')

    def __calc_col_widths(self, data: list[list[Paragraph]]) -> list[float]:
        style = self.table_style
        padding = style.left_padding + style.right_padding
        columns = utils.get_columns(data)
        base_width = self.table_width / len(columns)
        col_widths: list[float] = []
        for column in columns:
            col_width = 0
            for cell in column:
                cell.wrap(base_width, 0)
                width = cell._width_max
                offset = base_width - width
                width += offset / 2
                col_width = max(width, col_width)
            col_widths.append(col_width + padding)
        return col_widths

    def __calc_row_heights(self,
                           data: list[list[Paragraph]],
                           col_widths: list[float]
                          ) -> list[float]:
        style = self.table_style
        padding = style.top_padding + style.bottom_padding
        row_heights: list[float] = []
        for y, row in enumerate(data):
            row_height = 0
            for x, cell in enumerate(row):
                _, height = cell.wrap(col_widths[x], 0)
                style = self.style_matrix[y][x]
                row_height = max(height, row_height)
            row_heights.append(row_height + padding)
        return row_heights


class TableCell(Table):
    def __init__(self,
                 elements: list[ParagraphLine],
                 width: float,
                 style: BetterParagraphStyle | None=None,):
        self.elements = elements
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
                 data: list[list[ElementLine]],
                 measure: Measure | None=None,
                 headers: int=1,
                 determinants: int=0,
                 spans: list[_TABLE_SPAN] | None=None,
                 **kwargs):
        if kwargs != {}:
            Table.__init__(self, data, **kwargs)
            return

        self.data = data    
        self.measure = measure
        self.spans = spans or []
        self.style = get_table_style(data, headers, determinants, self.spans)
        self.span_dict = {str((y, x)): span_sizes
                            for (y, x), span_sizes in self.spans}
        self.table_cells = self.__convert_data()
        Table.__init__(self,
                       data=self.table_cells,
                       style=self.style,
                       colWidths=self.col_widths,
                       rowHeights=self.row_heights,
                       hAlign='LEFT')

    @property
    def col_widths(self) -> list[float]:
        try:
            return self.__col_widths
        except AttributeError:
            _col_widths = self.__calc_col_widths()
            widths_len = len(_col_widths)
            for y, row in enumerate(self.data):
                try:
                    assert len(row) == widths_len
                except AssertionError as err:
                    raise SummaryGenError(
                        f'the number of column widths {widths_len} does not'
                        f' match the amount of columns in row {y}'
                    ) from err
            self.__col_widths = _col_widths
            return self.__col_widths

    @property
    def row_heights(self) -> list[float]:
        try:
            return self.__row_heights
        except AttributeError:
            _row_heights = self.__calc_row_heights()
            rows = [row for row in zip(*self.data)]
            heights_len = len(_row_heights)
            for x, col in enumerate(rows):
                try:
                    assert len(col) == heights_len
                except AssertionError as err:
                    raise SummaryGenError(
                        f'the number of row heights {heights_len} does not'
                        f' match the amount of rows in column {x}'
                    ) from err
            self.__row_heights = _row_heights
            return self.__row_heights

    def __calc_col_widths(self) -> list[float]:
        headers = self.data[0]
        base_width = INNER_WIDTH / len(headers)
        width_matrix: list[list[float]] = []
        skip = 0
        for y, row in enumerate(self.data):
            matrix_row: list[float] = []
            for x in range(len(row)):
                if skip != 0:
                    skip -= 1
                    continue
                frags = wrap_elements(row[x].elements, max_width=base_width)
                if frags == []:
                    width = 0
                else:
                    width = max([line.width for line in frags])
                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    width_frags = [width / col_span] * col_span
                    width_frags[0] += self.style.left_padding
                    width_frags[-1] += self.style.right_padding
                    matrix_row.extend(width_frags)
                    skip = col_span - 1
                else:
                    width += self.style.left_padding + self.style.right_padding
                    matrix_row.append(width)
            width_matrix.append(matrix_row)

        for (y, x), (row_span, _) in self.spans:
            if row_span > 1:
                width = max([widths for widths in zip(*width_matrix)][x])
                for i in range(y, y + row_span):
                    width_matrix[i][x] = width

        return [max(widths) for widths in zip(*width_matrix)]

    def __calc_row_heights(self) -> list[float]:
        height_matrix: list[list[float]] = []
        skip = 0
        for y, row in enumerate(self.data):
            matrix_row: list[float] = []
            for x in range(len(row)):
                if skip != 0:
                    skip -= 1
                    continue
                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    col_width = sum(self.col_widths[x:x + col_span - 1])
                else:
                    col_width = self.col_widths[x]
                frags = wrap_elements(row[x].elements, col_width)
                height = row[x].height * len(frags)
                if col_span > 1:
                    height_frags = [height] * col_span
                    height_frags[0] += self.style.top_padding
                    height_frags[-1] += self.style.bottom_padding
                    matrix_row.extend(height_frags)
                    skip = col_span - 1
                else:
                    height += self.style.top_padding
                    height += self.style.bottom_padding
                    matrix_row.append(height)
            height_matrix.append(matrix_row)

        for (y, x), (row_span, _) in self.spans:
            if row_span > 1:
                col = [heights for heights in zip(*height_matrix)][x]
                height_frag = max(col) / row_span
                for i in range(y, y + row_span):
                    height_matrix[i][x] = height_frag

        return [max(heights) for heights in height_matrix]

    def __wrap_data(self) -> list[list[list[ElementLine]]]:
        h_padding = self.style.left_padding + self.style.right_padding
        cell_widths = [math.ceil(width - h_padding)
                        for width in self.col_widths]
        frags: list[list[list[ElementLine]]] = []
        for y, table_row in enumerate(self.data):
            frag_line: list[list[ElementLine]] = []
            for x, elem_line in enumerate(table_row):
                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    cell_width = sum(cell_widths[x:x + col_span - 1])
                else:
                    cell_width = cell_widths[x]
                frag_line.append(wrap_elements(elem_line.elements,
                                               max_width=cell_width))
            frags.append(frag_line)
        return frags

    def __convert_data(self) -> list[list[TableCell | str]]:
        frags = self.__wrap_data()
        table_cells: list[list[TableCell | str]] = []
        for y, frag_line in enumerate(frags):
            cells: list[TableCell | str] = []
            for x, table_cell in enumerate(frag_line):
                if table_cell == []:
                    cell = ''
                else:
                    cell_lines: list[ParagraphLine] = []
                    for element_line in table_cell:
                        para_line = ParagraphLine(element_line=element_line,
                                                  measure=self.measure)
                        cell_lines.append(para_line)
                    _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                    if col_span > 1:
                        col_width = sum(self.col_widths[x:x + col_span - 1])
                    else:
                        col_width = self.col_widths[x]
                    cell = TableCell(cell_lines, width=col_width)
                cells.append(cell)
            table_cells.append(cells)
        return table_cells


class ValueTableHeader(Paragraph):
    def __init__(self, text: str, link: str | None=None):
        header_text = text
        if link != None:
            header_text = f'<link href=\"{link}\">{header_text}</link>'
            style = PSTYLES['h6Link']
        else:
            style = PSTYLES['h6']
        Paragraph.__init__(self, header_text, style=style)


class EmbeddedValueTable(KeepTogether):
    def __init__(self, table_info: VTObjectInfo, measure: Measure):
        self.info = table_info
        self.measure = measure
        self.value_table = self.__get_table()
        table = ValueTable(data=self.__get_content(),
                           measure=self.measure,
                           determinants=len(self.value_table.determinants))
        change_id = self.info.change_url.split('/')[4]
        table_link = f'{self.measure.link}/value-table/{change_id}/'
        header = ValueTableHeader(self.value_table.name, table_link)
        KeepTogether.__init__(self, [header, table])

    def __get_table(self) -> ValueTableObject:
        possible_names = [
            self.info.api_name_unique,
            self.info.title,
            self.info.verbose_name
        ]

        value_table: ValueTableObject | None = None
        for name in possible_names:
            value_table = self.measure.get_value_table(name)
            if value_table != None:
                break

        if value_table == None:
            raise SummaryGenError(f'value table {self.info.verbose_name}'
                                  ' does not exist in measure'
                                  f' {self.measure.full_version_id}')

        return value_table

    def __get_headers(self) -> list[ElementLine]:
        headers: list[ElementLine] = []
        for api_name in self.value_table.determinants:
            determinant = self.measure.get_determinant(api_name)
            element_line = ElementLine(max_width=None,
                                       style=PSTYLES['ValueTableHeader'])
            element = ParagraphElement(text=determinant.name)
            element_line.add(element)
            headers.append(element_line)
        for column in self.value_table.columns:
            element_line = ElementLine(max_width=None)
            text = f'{column.name} ({column.unit})'
            text_element = ParagraphElement(text=text,
                                            style=PSTYLES['ValueTableHeader'])
            element_line.add(text_element)
            for ref in column.reference_refs:
                ref_element = ParagraphElement(text=ref, type=ElemType.REF)
                element_line.add(ref_element)
            headers.append(element_line)
        return headers

    def __get_body(self) -> list[list[ElementLine]]:
        body: list[list[ElementLine]] = []
        for row in self.value_table.values:
            table_row: list[ElementLine] = []
            for i, item in enumerate(row):
                if i < len(self.value_table.determinants):
                    style = PSTYLES['ValueTableDeterminant']
                else:
                    style = PSTYLES['ValueTableItem']
                if item is None:
                    text = ''
                else:
                    text = item
                element = ParagraphElement(text)
                table_row.append(ElementLine(elements=[element], style=style))
            body.append(table_row)
        return body

    def __get_content(self) -> list[list[ElementLine]]:
        return [self.__get_headers(), *self.__get_body()]
