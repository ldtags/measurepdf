import math
from typing import Literal
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Table,
    Paragraph,
    Flowable
)

from src import utils
from src.etrm.models import Measure
from src.resources import SunsettedMeasureCollection
from src.summarygen.utils import get_flowable_height, get_flowable_width
from src.summarygen.types import _TableOrient, _TableSpan
from src.summarygen.styles import (
    ParagraphStyle,
    TableStyle,
    PSTYLES,
    TSTYLES,
    INNER_WIDTH,
    DEF_PSTYLE,
    get_table_style,
    get_sunsetted_measures_table_style
)
from src.summarygen.models import (
    VTObjectInfo,
    ParagraphElement,
    ElementLine,
    ElementType
)
from src.summarygen.flowables.utils import wrap_elements
from src.summarygen.flowables.paragraph import ParagraphLine
from src.summarygen.exceptions import SummaryGenError


class TableCell(Table):
    def __init__(
        self,
        elements: list[ParagraphLine],
        width: float = INNER_WIDTH,
        style: ParagraphStyle | None = None,
        **kwargs
    ) -> None:
        if kwargs.get("normalizedData", None) is not None:
            Table.__init__(self, elements, **kwargs)
            return

        self.elements = elements
        self.max_width = width
        self.pstyle = style
        if elements == []:
            elem_line = ElementLine(string="", style=style)
            self.elements.append(ParagraphLine(elem_line))

        super().__init__(
            self.line_matrix,
            colWidths=self.width,
            rowHeights=self.row_heights,
            style=TSTYLES["Unstyled"],
            hAlign="LEFT"
        )

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
        data: list[list[str | ElementLine | Flowable]],
        headers: int = 1,
        measure: Measure | None = None,
        spans: list[_TableSpan] | None = None,
        header_styles: _TABLE_STYLES = PSTYLES["ValueTableHeader"],
        body_col_styles: _TABLE_STYLES | None = None,
        body_row_styles: _TABLE_STYLES | None = None,
        table_style: TableStyle | None = None,
        col_widths: list[float] | float | None = None,
        row_heights: list[float] | float | None = None,
        h_align: Literal["left", "center", "right"] = "left",
        repeat_rows: int = 1,
        max_width: float = INNER_WIDTH,
        min_col_widths: bool = False,
        x_padding: int = 0,
        y_padding: int = 0,
        **kwargs
    ) -> None:
        """Constructs a ReportLab `Table` with the provided data.

        Args:
            - data : A 2D matrix of strings, `ElementLine` objects or flowables
            that define the table data.

            ` headers : A non-negative integer representing the number of
            rows/cols (depending on `header_orient`) that are table headers.

            - measure : An eTRM measure object, used for adding links and data
            that would otherwise be unaccessible.

            - spans : A list of table spans that exist within the table. A
            table span is a two-tuple of two-tuples. The first two-tuple
            contains the (y, x) coords of the first cell in the span. The
            second two-tuple contains the (row, column) span sizes of the
            span. The span sizes should include the initial cell.

            - header_orient : The orientation of the table header.

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

        # Allow reportlab to do the final pass in the multiBuild process
        if kwargs.get("normalizedData") is not None:
            super().__init__(data, **kwargs)
            return

        # Validate input data
        assert data != []
        assert headers > -1

        # Ensure that each cell in each row has an associated size
        row_len: float | None = None
        for row in data:
            if row_len is None:
                row_len = len(row)
            else:
                assert len(row) == row_len

        assert row_len is not None

        self.header_count = headers
        self.measure = measure
        self.max_width = max_width
        self.spans = spans or []
        self.span_dict = {
            str((y, x)): span_sizes
                for (y, x), span_sizes
                in self.spans
        }

        # Apply the table style
        self.style = table_style or get_table_style(
            data=data,
            headers=headers,
            determinants=row_len,
            spans=self.spans
        )
        self.h_padding = self.style.left_padding + self.style.right_padding
        self.v_padding = self.style.top_padding + self.style.bottom_padding

        # Apply the header styles
        style_count = len(data[0])
        if isinstance(header_styles, ParagraphStyle):
            self.header_styles = [header_styles] * style_count
        else:
            assert len(header_styles) == headers
            self.header_styles = header_styles

        self._body_style_orient: Literal["row", "col"] | None = None
        body_styles = []
        if body_col_styles is not None:
            self._body_style_orient = "col"
            body_styles = body_col_styles
        elif body_row_styles is not None:
            self._body_style_orient = "row"
            body_styles = body_row_styles
            style_count = len(data) - headers
        else:
            body_styles = PSTYLES["ValueTableDeterminant"]

        # Apply the body styles
        if isinstance(body_styles, ParagraphStyle):
            self.body_styles = [body_styles] * style_count
        else:
            assert len(body_styles) == style_count
            self.body_styles = body_styles

        # Convert raw strings into element lines
        self.data = self._sanitize_data(data)

        # Ensure that each column has a defined width
        if isinstance(col_widths, float):
            self.col_widths = [col_widths] * row_len
        elif col_widths is not None:
            assert row_len == len(col_widths)
            self.col_widths = col_widths
        else:
            self.col_widths = self._calc_col_widths(self.data)

        # Ensure that each row has a defined height
        if isinstance(row_heights, float):
            self.row_heights = [row_heights] * len(data)
        elif row_heights is not None:
            assert len(data) == len(row_heights)
            self.row_heights = row_heights
        else:
            self.row_heights = self._calc_row_heights(self.data)

        # Convert element lines into table cells
        self.table_cells = self._convert_data(self.data)

        # Pull headers from the table data
        self.headers = self.table_cells[0:headers]

        # Apply horizontal padding to column widths
        for i, val in enumerate(self.col_widths):
            self.col_widths[i] = val + x_padding

        # Apply vertical padding to row heights
        for i, val in enumerate(self.row_heights):
            self.row_heights[i] = val + y_padding

        # Force minimum column width if specified
        if min_col_widths:
            _min_col_widths = [0] * len(self.col_widths)
            for y, row in enumerate(self.table_cells):
                for x, item in enumerate(row):
                    if isinstance(item, TableCell):
                        width = item.get_min_width()
                    elif isinstance(item, Flowable):
                        width, _ = item.wrap(self.col_widths[x], self.row_heights[y])
                    else:
                        width = stringWidth(
                            item,
                            self.body_styles[0].font_name,
                            self.body_styles[0].font_size
                        )

                    width += x_padding
                    if width > _min_col_widths[x]:
                        _min_col_widths[x] = width

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
        is_header = y < self.header_count
        if is_header:
            return self.header_styles[y]

        if self._body_style_orient == "row":
            return self.body_styles[y - self.header_count]

        return self.body_styles[x]

    def _sanitize_data(
        self,
        data: list[list[str | ElementLine | Flowable]]
    ) -> list[list[ElementLine | Flowable]]:
        sanitized_data: list[list[ElementLine | Flowable]] = []
        for y, row in enumerate(data):
            sanitized_row: list[ElementLine | Flowable] = []
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

    def _calc_min_widths(
        self,
        data: list[list[ElementLine | Flowable]],
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

                # Probably not correct as flowables can be wrapped in a
                # table, but whatever
                if isinstance(cell, Flowable):
                    width = get_flowable_width(cell)
                else:
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

    def _calc_col_widths(self, data: list[list[ElementLine | Flowable]]) -> list[float]:
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

    def _calc_row_heights(
        self,
        data: list[list[ElementLine | Flowable]],
        col_widths: list[float] | None = None
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
            for x, cell in enumerate(row):
                if skip != 0:
                    skip -= 1
                    continue

                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    col_width = sum(_col_widths[x:x + col_span - 1])
                else:
                    col_width = _col_widths[x]

                # Also probably not correct for the same reasons as the widths
                if isinstance(cell, Flowable):
                    height = get_flowable_height(cell)
                else:
                    frags = wrap_elements(cell.elements, col_width - h_padding)
                    height = cell.height * len(frags)

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

    def _wrap_data(
        self,
        data: list[list[ElementLine | Flowable]]
    ) -> list[list[list[ElementLine] | Flowable]]:
        h_padding = self.style.left_padding + self.style.right_padding
        cell_widths = [
            math.ceil(width - h_padding)
            for width
            in self.col_widths
        ]
        frags: list[list[list[ElementLine] | Flowable]] = []
        for y, table_row in enumerate(data):
            frag_line: list[list[ElementLine] | Flowable] = []
            for x, cell in enumerate(table_row):
                _, col_span = self.span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    cell_width = sum(cell_widths[x:x + col_span - 1])
                else:
                    cell_width = cell_widths[x]

                if isinstance(cell, Flowable):
                    frag_line.append(cell)
                else:
                    elements = cell.elements
                    for element in elements:
                        if not element.is_styled():
                            element.style = self.get_style(x, y)

                    frag_line.append(
                        wrap_elements(cell.elements, max_width=cell_width)
                    )

            frags.append(frag_line)

        return frags

    def _convert_data(
        self,
        data: list[list[ElementLine | Flowable]]
    ) -> list[list[TableCell | Flowable | str]]:
        frags = self._wrap_data(data)
        table_cells: list[list[TableCell | Flowable | str]] = []
        for y, frag_line in enumerate(frags):
            cells: list[TableCell | Flowable | str] = []
            for x, cell in enumerate(frag_line):
                if isinstance(cell, Flowable):
                    cells.append(cell)
                    continue

                if cell == []:
                    cell = ""
                else:
                    cell_lines: list[ParagraphLine] = []
                    for element_line in cell:
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
    def __init__(
        self,
        data: list[list[ElementLine]],
        measure: Measure | None = None,
        headers: int = 1,
        determinants: int = 0,
        spans: list[_TableSpan] | None = None,
        **kwargs
    ) -> None:
        if kwargs.get("normalizedData") is not None:
            Table.__init__(self, data, **kwargs)
            return

        style = get_table_style(
            data=data,
            headers=headers,
            determinants=determinants,
            spans=spans or []
        )

        super().__init__(
            data=data,
            headers=headers,
            measure=measure,
            spans=spans,
            table_style=style
        )


class ValueTableHeader(Paragraph):
    def __init__(self, table_info: VTObjectInfo, measure: Measure) -> None:
        value_table = measure.get_value_table(*table_info.possible_names)
        if value_table is None:
            raise SummaryGenError(f"Invalid value table info: {table_info}")

        change_id = table_info.change_url.split("/")[4]
        link = f"{measure.link}/value-table/{change_id}/"
        text = f"<link href=\"{link}\">{value_table.name}</link>"
        Paragraph.__init__(self, text, style=PSTYLES["h6Link"])


class EmbeddedValueTable(ValueTable):
    def __init__(
        self,
        table_info: VTObjectInfo,
        measure: Measure | None = None,
        **kwargs
    ) -> None:
        if kwargs.get("normalizedData", None) is not None:
            Table.__init__(self, table_info, **kwargs)
            return

        if measure is None:
            raise SummaryGenError(
                "Cannot generate a value table without an eTRM measure"
            )

        self.measure = measure
        self.value_table = measure.get_value_table(*table_info.possible_names)
        if self.value_table is None:
            raise SummaryGenError(f'Invalid value table info: {table_info}')

        super().__init__(
            data=self._get_content(),
            measure=self.measure,
            determinants=len(self.value_table.determinants)
        )

    def _get_headers(self) -> list[ElementLine]:
        headers: list[ElementLine] = []
        for api_name in self.value_table.determinants:
            determinant = self.measure.get_determinant(api_name)
            if determinant is None:
                continue

            element_line = ElementLine(max_width=None)
            text = determinant.name.upper()
            element = ParagraphElement(
                text=text,
                style=PSTYLES["ValueTableHeader"]
            )
            element_line.add(element)
            headers.append(element_line)

        for column in self.value_table.columns:
            element_line = ElementLine(max_width=None)
            text = f"{column.name} ({column.unit})".upper()
            element = ParagraphElement(
                text=text,
                style=PSTYLES["ValueTableHeader"]
            )
            element_line.add(element)
            for ref in column.reference_refs:
                ref_element = ParagraphElement(
                    text=ref,
                    type=ElementType.Reference,
                    style=PSTYLES["VTHeaderRefTag"]
                )
                element_line.add(ref_element)

            headers.append(element_line)

        return headers

    def _get_body(self) -> list[list[ElementLine]]:
        body: list[list[ElementLine]] = []
        for row in self.value_table.values:
            table_row: list[ElementLine] = []
            for i, item in enumerate(row):
                if i < len(self.value_table.determinants):
                    style = PSTYLES["ValueTableDeterminant"]
                else:
                    style = PSTYLES["ValueTableItem"]

                if item is None:
                    text = ""
                else:
                    text = item

                element = ParagraphElement(text)
                table_row.append(ElementLine(elements=[element], style=style))

            body.append(table_row)

        return body

    def _get_content(self) -> list[list[ElementLine]]:
        headers = self._get_headers()
        body = self._get_body()
        sanitized_headers: list[ElementLine] = []
        sanitized_cols: list[list[ElementLine]] = []
        for x, col in enumerate(utils.rotate_matrix(body)):
            if not all([elem.text == "" for elem in col]):
                sanitized_cols.append(col)
                sanitized_headers.append(headers[x])

        sanitized_cols = utils.rotate_matrix(sanitized_cols)
        return [sanitized_headers, *sanitized_cols]


class SunsettedMeasuresTable(BasicTable):
    def __init__(self, use_categories: list[SunsettedMeasureCollection], **kw) -> None:
        if kw.get("normalizedData") is not None:
            Table.__init__(self, use_categories, **kw)
            return

        headers = [
            "",
            "Measure Version ID",
            "Measure Name",
            "Start Date - End Date",
            "TRM Update",
            "Measure Version Update",
            "Measure Sunsetted / Deactivated"
        ]

        data = [headers]
        uc_row_indices: list[int] = []
        spans: list[_TableSpan] = []
        for i, use_category in enumerate(use_categories):
            data.append([use_category.name, "", "", "", "", "", ""])
            row_index = len(data) - 1
            uc_row_indices.append(row_index)
            spans.append(((row_index, 0), (0, 7)))
            if use_category.measures == []:
                data.append(["", "", "", " ", "", "", ""])

            for measure in use_category.measures:
                data.append(
                    [
                        "",
                        measure.version_id,
                        measure.name,
                        measure.active_life,
                        "X" if measure.trm_update else "",
                        "X" if measure.version_update else "",
                        "X" if measure.is_sunsetted else ""
                    ]
                )

            if i != len(use_categories) - 1:
                data.append(["", "", "", " ", "", "", ""])

        cur_life: str | None = None
        cur_span: _TableSpan | None = None
        for y, row in enumerate(data):
            if cur_life is None or row[3] != cur_life:
                if cur_span is not None and cur_span[1][0] != 1:
                    spans.append(cur_span)

                cur_life = row[3]
                cur_span = ((y, 3), (1, 0))
                continue

            row[3] = ""
            if cur_span is not None:
                cur_span = (cur_span[0], (cur_span[1][0] + 1, cur_span[1][1]))

        if cur_span is not None and cur_span[1][0] != 1:
            spans.append(cur_span)

        uc_row_indice_set = set(uc_row_indices)
        para_styles: list[ParagraphStyle] = []
        for y in range(1, len(data)):
            if y in uc_row_indice_set:
                para_styles.append(DEF_PSTYLE.bold)
            else:
                para_styles.append(DEF_PSTYLE)

        super().__init__(
            data,
            header_styles=DEF_PSTYLE.bold,
            body_row_styles=para_styles,
            table_style=get_sunsetted_measures_table_style(len(data), spans, uc_row_indices),
            spans=spans,
            **kw
        )
