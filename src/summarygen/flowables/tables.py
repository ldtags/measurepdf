import math
from typing import Literal
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Table,
    Paragraph
)

from src import utils
from src.etrm.models import Measure
from src.summarygen.models.enums import ElementType
from src.summarygen.types import _TableOrient, _TableSpan
from src.summarygen.styles import (
    ParagraphStyle,
    TableStyle,
    PSTYLES,
    TSTYLES,
    INNER_WIDTH,
    get_table_style
)
from src.summarygen.models import (
    VTObjectInfo,
    ParagraphElement,
    ElementLine
)
from src.summarygen.flowables.utils import wrap_elements
from src.summarygen.flowables.paragraph import ParagraphLine
from src.summarygen.exceptions import SummaryGenError


class TableCell(Table):
    def __init__(self,
                 elements: list[ParagraphLine],
                 width: float=INNER_WIDTH,
                 style: ParagraphStyle | None=None,
                 **kwargs):
        if kwargs.get('normalizedData', None) is not None:
            Table.__init__(self, elements, **kwargs)
            return

        self.elements = elements
        self.max_width = width
        self.pstyle = style
        if elements == []:
            elem_line = ElementLine(string='', style=style)
            self.elements.append(ParagraphLine(elem_line))
        Table.__init__(self,
                       self.line_matrix,
                       colWidths=self.width,
                       rowHeights=self.row_heights,
                       style=TSTYLES['Unstyled'],
                       hAlign='LEFT')

    @property
    def line_matrix(self) -> list[list[ParagraphLine]]:
        return [[elem] for elem in self.elements]

    @property
    def width(self) -> float:
        return max([line.width for line in self.elements])

    def get_min_width(self) -> float:
        return max([line.width for line in self.elements])

    @property
    def row_heights(self) -> list[float]:
        return [elem.height for elem in self.elements]


_TABLE_STYLES = list[ParagraphStyle] | ParagraphStyle


class BasicTable(Table):
    """Base class for tables in the summary PDF.

    Use when creating a new table or extend to create a new table class.

    Do not use when creating a new class that will extend the
    `Table` class, but will not be a genuine table (i.e., `TableCell`,
    `ParagraphLine`).
    """

    def __init__(
        self,
        data: list[list[str | ElementLine]],
        headers: int = 1,
        measure: Measure | None = None,
        spans: list[_TableSpan] | None = None,
        header_orient: _TableOrient = "top",
        header_styles: _TABLE_STYLES = PSTYLES["ValueTableHeader"],
        body_styles: _TABLE_STYLES = PSTYLES["ValueTableDeterminant"],
        table_style: TableStyle | None = None,
        col_widths: list[float] | float | None = None,
        row_heights: list[float] | float | None = None,
        h_align: Literal["left", "center", "right"] = "left",
        repeat_rows: int = 1,
        max_width: float = INNER_WIDTH,
        min_col_widths: bool = False,
        x_padding: int = 0,
        y_padding: int = 0,
        uniform_columns: bool = False,
        **kwargs
    ) -> None:
        """Constructs a ReportLab `Table` with the provided data.

        Parameters:
            `data` - A 2D matrix of strings or `ElementLine` objects that
            define the table data.

            `headers` - A non-negative integer representing the number of
            rows/cols (depending on `header_orient`) that are table headers.

            `measure` - An eTRM measure object, used for adding links and data
            that would otherwise be unaccessible.

            `spans` - A list of table spans that exist within the table. A
            table span is a two-tuple of two-tuples. The first two-tuple
            contains the (y, x) coords of the first cell in the span. The
            second two-tuple contains the (row, column) span sizes of the
            span. The span sizes should include the initial cell.

            `header_orient` - The orientation of the table header.

            `header_styles` - A list of paragraph styles that define how the
            elements within the table headers should be styled. If only one
            style is provided, that style will be used for each table header.
            Otherwise, a style must be provided for each header col ('top'
            `header_orient`) or row ('left' `header_orient`).

            `body_styles` - A list of paragraph styles that define how the
            elements within the table body should be styled. These follow the
            same structure as the `header_styles`.

            `table_style` - A ReportLab `TableStyle`. If none is provided, the
            default table style is applied.

            `col_widths` - A list of floats that define the widths of each
            column in the table. If none are provided, they are calculated
            based on the contents of `data` to fit the page size.

            `row_heights` - A list of floats the define the heights of each
            row in the table. If none are provided, they are calculated based
            on the contents of `data` to fit the provided or calculated column
            widths.

            `h_align` - The horizontal aligmnent of the table.

            `repeat_rows` - The number of table rows that will be repeated
            in the event of a table split.
        """

        # Allows reportlab to do the final pass in the multiBuild process
        if kwargs.get("normalizedData") is not None:
            super().__init__(data, **kwargs)
            return

        # Validates input data
        assert data != []
        assert headers > -1

        # Ensures that each cell in each row has an associated size
        row_len: float | None = None
        for row in data:
            if row_len is None:
                row_len = len(row)
            else:
                assert len(row) == row_len

        assert row_len is not None

        self.uniform_columns = uniform_columns
        self.header_count = headers
        self.header_orient = header_orient
        self.measure = measure
        self.max_width = max_width
        self.spans = spans or []
        self.span_dict = {
            str((y, x)): span_sizes
                for (y, x), span_sizes
                in self.spans
        }

        # Applies the table style
        self.style = table_style or get_table_style(
            data=data,
            headers=headers,
            determinants=row_len,
            spans=self.spans
        )
        self.h_padding = self.style.left_padding + self.style.right_padding
        self.v_padding = self.style.top_padding + self.style.bottom_padding

        # Applies the header styles
        style_count = row_len if header_orient == "top" else len(data)
        if isinstance(header_styles, ParagraphStyle):
            self.header_styles = [header_styles] * style_count
        else:
            assert len(header_styles) == headers
            self.header_styles = header_styles

        # Applies the body styles
        if isinstance(body_styles, ParagraphStyle):
            self.body_styles = [body_styles] * style_count
        else:
            assert len(body_styles) == style_count
            self.body_styles = body_styles

        self.data = self._sanitize_data(data)

        # Ensures that each column has a defined width
        if isinstance(col_widths, float):
            self.col_widths = [col_widths] * row_len
        elif col_widths is not None:
            assert row_len == len(col_widths)
            self.col_widths = col_widths
        else:
            self.col_widths = self._calc_col_widths(self.data)

        # Ensures that each row has a defined height
        if isinstance(row_heights, float):
            self.row_heights = [row_heights] * len(data)
        elif row_heights is not None:
            assert len(data) == len(row_heights)
            self.row_heights = row_heights
        else:
            self.row_heights = self._calc_row_heights(self.data)

        self.table_cells = self._convert_data(self.data)

        # Pulls headers from the table data
        if header_orient == "left":
            columns = utils.rotate_matrix(self.table_cells)
            self.headers = columns[0:headers]
        else:
            self.headers = self.table_cells[0:headers]

        for i, val in enumerate(self.col_widths):
            self.col_widths[i] = val + x_padding

        for i, val in enumerate(self.row_heights):
            self.row_heights[i] = val + y_padding

        _min_col_widths = [0] * len(self.col_widths)
        if min_col_widths:
            for row in self.table_cells:
                for i, item in enumerate(row):
                    if isinstance(item, TableCell):
                        width = item.get_min_width()
                    else:
                        width = stringWidth(
                            item,
                            self.body_styles[0].font_name,
                            self.body_styles[0].font_size
                        )

                    width += x_padding
                    if width > _min_col_widths[i]:
                        _min_col_widths[i] = width

            self.col_widths = _min_col_widths

        super().__init__(
            data=self.table_cells,
            colWidths=self.col_widths,
            rowHeights=self.row_heights,
            style=self.style,
            hAlign=h_align.upper(),
            repeatRows=repeat_rows,
            **kwargs
        )

    def get_style(self, x: int, y: int) -> ParagraphStyle:
        if self.header_orient == 'left':
            is_header = x < self.header_count
            head_axis = x
            body_off = self.header_count
        else:
            is_header = y < self.header_count
            head_axis = y
            body_off = 0

        if is_header:
            return self.header_styles[head_axis]

        return self.body_styles[x - body_off]

    def _calc_min_widths(
        self,
        data: list[list[ElementLine]],
        size: int = 1
    ) -> list[list[float]]:
        """Calculates the minimum width of each column in `data` given
        that each table cell will use, at most, `size` amount of words.

        If a table cell has less than `size` words, it will not be wrapped.
        """

        min_matrix: list[list[float]] = []
        for y, row in enumerate(data):
            skip = 0
            matrix_row: list[float] = []
            for x, cell in enumerate(row):
                if skip > 0:
                    skip -= 1
                    continue

                width = cell.get_min_width(size)
                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    width_frags = [width / col_span] * col_span
                    width_frags[0] += self.style.left_padding
                    width_frags[-1] += self.style.right_padding
                    matrix_row.extend(width_frags)
                    skip = col_span - 1
                    continue

                matrix_row.append(width + self.h_padding)

            min_matrix.append(matrix_row)

        for (y, x), (row_span, _) in self.spans:
            if row_span > 1:
                columns = utils.rotate_matrix(min_matrix)
                width = max(columns[x])
                for i in range(y, y + row_span):
                    min_matrix[i][x] = width

        return [max(column) for column in utils.rotate_matrix(min_matrix)]

    def _calc_col_widths(self, data: list[list[ElementLine]]) -> list[float]:
        """Returns the list of column widths for this table.

        Column widths are calculated by unwrapping data until it cannot
        unwrap without exceeding the max width.

        This method directly joins previously split elements, avoiding the
        costly `wrap_elements` method.
        """

        size = 1
        prev_widths = self._calc_min_widths(data, size)
        while math.fsum(prev_widths) <= self.max_width:
            col_widths = self._calc_min_widths(data, size=size + 1)
            if col_widths == prev_widths:
                break

            if math.fsum(col_widths) > self.max_width:
                differences: list[tuple[int, float]] = []
                for i, width in enumerate(col_widths):
                    differences.append((i, width - prev_widths[i]))

                differences.sort(key=lambda t: t[1], reverse=True)
                for difference in differences:
                    index = difference[0]
                    amount = difference[1]
                    widths = prev_widths.copy()
                    widths[index] += amount
                    if math.fsum(widths) > self.max_width:
                        break

                    prev_widths[index] += amount

                break

            size += 1
            prev_widths = col_widths

        if math.fsum(prev_widths) > self.max_width:
            raise SummaryGenError('Table is too large for the PDF')

        rem_width = self.max_width - math.fsum(prev_widths)
        add_width = rem_width / len(prev_widths)
        prev_widths = [width + add_width for width in prev_widths]
        return prev_widths

    def _calc_row_heights(self,
                           data: list[list[ElementLine]],
                           col_widths: list[float] | None=None
                          ) -> list[float]:
        """Calculates the heights of each row of the table by wrapping
        all data to fit within the previously calculated `col_widths`.
        """

        _col_widths = col_widths or self.col_widths
        h_padding = self.style.left_padding + self.style.right_padding
        height_matrix: list[list[float]] = []
        skip = 0
        for y, row in enumerate(data):
            assert len(row) == len(_col_widths)
            matrix_row: list[float] = []
            for x in range(len(row)):
                if skip != 0:
                    skip -= 1
                    continue

                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    col_width = sum(_col_widths[x:x + col_span - 1])
                else:
                    col_width = _col_widths[x]

                frags = wrap_elements(row[x].elements, col_width - h_padding)
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

    def _sanitize_data(
        self,
        data: list[list[ElementLine | str]]
    ) -> list[list[ElementLine]]:
        sanitized_data: list[list[ElementLine]] = []
        for y, row in enumerate(data):
            sanitized_row: list[ElementLine] = []
            for x, cell in enumerate(row):
                if isinstance(cell, str):
                    style = self.get_style(x, y)
                    elem = ElementLine(
                        string=cell,
                        style=style,
                        max_width=None
                    )
                else:
                    elem = cell

                sanitized_row.append(elem)

            sanitized_data.append(sanitized_row)

        return sanitized_data

    def _wrap_data(
        self,
        data: list[list[ElementLine]]
    ) -> list[list[list[ElementLine]]]:
        h_padding = self.style.left_padding + self.style.right_padding
        cell_widths = [
            math.ceil(width - h_padding)
            for width
            in self.col_widths
        ]
        frags: list[list[list[ElementLine]]] = []
        for y, table_row in enumerate(data):
            frag_line: list[list[ElementLine]] = []
            for x, elem_line in enumerate(table_row):
                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    cell_width = sum(cell_widths[x:x + col_span - 1])
                else:
                    cell_width = cell_widths[x]

                elements = elem_line.elements
                for element in elements:
                    if not element.is_styled():
                        element.style = self.get_style(x, y)

                frag_line.append(
                    wrap_elements(elem_line.elements, max_width=cell_width)
                )

            frags.append(frag_line)

        return frags

    def _convert_data(
        self,
        data: list[list[ElementLine]]
    ) -> list[list[TableCell | str]]:
        frags = self._wrap_data(data)
        table_cells: list[list[TableCell | str]] = []
        for y, frag_line in enumerate(frags):
            cells: list[TableCell | str] = []
            for x, table_cell in enumerate(frag_line):
                if table_cell == []:
                    cell = ''
                else:
                    cell_lines: list[ParagraphLine] = []
                    for element_line in table_cell:
                        para_line = ParagraphLine(
                            element_line=element_line,
                            measure=self.measure
                        )
                        cell_lines.append(para_line)

                    _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                    if col_span > 1:
                        col_width = sum(self.col_widths[x:x + col_span - 1])
                    else:
                        col_width = self.col_widths[x]

                    col_width -= self.h_padding
                    cell = TableCell(cell_lines, width=col_width)

                cells.append(cell)

            table_cells.append(cells)

        return table_cells


class ValueTable(BasicTable):
    def __init__(self,
                 data: list[list[ElementLine]],
                 measure: Measure | None=None,
                 headers: int=1,
                 determinants: int=0,
                 spans: list[_TableSpan] | None=None,
                 **kwargs):
        if kwargs.get('normalizedData') is not None:
            Table.__init__(self, data, **kwargs)
            return

        style = get_table_style(data=data,
                                headers=headers,
                                determinants=determinants,
                                spans=spans or [])

        BasicTable.__init__(self,
                            data=data,
                            headers=headers,
                            measure=measure,
                            spans=spans,
                            table_style=style)


class ValueTableHeader(Paragraph):
    def __init__(self, table_info: VTObjectInfo, measure: Measure):
        value_table = measure.get_value_table(*table_info.possible_names)
        if value_table is None:
            raise SummaryGenError(f'Invalid value table info: {table_info}')

        change_id = table_info.change_url.split('/')[4]
        link = f'{measure.link}/value-table/{change_id}/'
        text = f'<link href=\"{link}\">{value_table.name}</link>'
        Paragraph.__init__(self, text, style=PSTYLES['h6Link'])


class EmbeddedValueTable(ValueTable):
    def __init__(self,
                 table_info: VTObjectInfo,
                 measure: Measure | None=None,
                 **kwargs):
        if kwargs.get('normalizedData', None) is not None:
            Table.__init__(self, table_info, **kwargs)
            return

        if measure is None:
            raise SummaryGenError('Cannot generate a value table without'
                                  ' an eTRM measure')

        self.measure = measure
        self.value_table = measure.get_value_table(*table_info.possible_names)
        if self.value_table is None:
            raise SummaryGenError(f'Invalid value table info: {table_info}')

        ValueTable.__init__(self,
                            data=self.__get_content(),
                            measure=self.measure,
                            determinants=len(self.value_table.determinants))

    def __get_headers(self) -> list[ElementLine]:
        headers: list[ElementLine] = []
        for api_name in self.value_table.determinants:
            determinant = self.measure.get_determinant(api_name)
            if determinant is None:
                continue
            element_line = ElementLine(max_width=None)
            text = determinant.name.upper()
            element = ParagraphElement(text=text,
                                       style=PSTYLES['ValueTableHeader'])
            element_line.add(element)
            headers.append(element_line)
        for column in self.value_table.columns:
            element_line = ElementLine(max_width=None)
            text = f'{column.name} ({column.unit})'.upper()
            element = ParagraphElement(text=text,
                                       style=PSTYLES['ValueTableHeader'])
            element_line.add(element)
            for ref in column.reference_refs:
                ref_element = ParagraphElement(text=ref,
                                               type=ElementType.Reference,
                                               style=PSTYLES['VTHeaderRefTag'])
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
        headers = self.__get_headers()
        body = self.__get_body()
        sanitized_headers: list[ElementLine] = []
        sanitized_cols: list[list[ElementLine]] = []
        for x, col in enumerate(utils.rotate_matrix(body)):
            if not all([elem.text == '' for elem in col]):
                sanitized_cols.append(col)
                sanitized_headers.append(headers[x])
        sanitized_cols = utils.rotate_matrix(sanitized_cols)
        return [sanitized_headers, *sanitized_cols]
