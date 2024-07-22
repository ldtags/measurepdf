"""Module for all custom flowables.

This module contains all custom flowables that are used within the 
summary PDF generation process. When creating a new custom flowable,
add it to this module.

Extending Custom Tables:
    ReportLab uses a weird process for constructing instances of
    the Table class. From my testing and looking through the source
    code, it seems that if the Table instance was constructed with both
    strings and flowables, the constructor will be called again. This is
    referred to as the "data normalization" process and a specific keyword
    arg (normalizedData) will be passed as a signifier. This makes extending
    the Table class weird, but doable. Examples of how to accommodate this
    process can be found in the custom Table flowables below.
"""


from __future__ import annotations
import math
import copy
from typing import Literal
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfgen.pathobject import PDFPathObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    XPreformatted,
    Spacer as _Spacer,
    KeepTogether
)

from src import utils, lookups, _SYSTEM, _NOW
from src.etrm.models import Measure
from src.summarygen.types import _TABLE_SPAN, _TABLE_ORIENT
from src.summarygen.models import VTObjectInfo
from src.summarygen.styles import (
    ParagraphStyle,
    TableStyle,
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES,
    INNER_WIDTH,
    INNER_HEIGHT,
    COLORS,
    _NL_HEIGHT,
    get_table_style
)
from src.summarygen.rlobjects import (
    ElemType,
    ParagraphElement,
    ElementLine
)
from src.summarygen.exceptions import (
    WidthExceededError,
    SummaryGenError
)


class Spacer(_Spacer):
    """Overwrites the ReportLab `Spacer` class to shrink in order
    to not exceed frame heights.
    """

    def wrap(self, availWidth, availHeight):
        height = min(self.height, availHeight - 1e-8)
        return (availWidth, height)


NEWLINE = Spacer(1, _NL_HEIGHT, isGlue=True)


class TitleSection(Flowable):
    """Custom flowable for an object with 1-2 lines of text that has
    an orange-brown rectangle to its left/right.

    Used on the measure title pages.
    """

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


class TitleSectionSubContainer(Table):
    """Container for a single column of title sections."""

    def __init__(self,
                 sections: list[TitleSection],
                 side: Literal['left', 'right']='left',
                 offset_height: float=25,
                 **kwargs):
        self.__col_width: float | None = None
        self.__row_heights: list[float] = []
        self.__sections = sections
        self.offset_height = offset_height

        if side == 'left':
            style = TSTYLES['TitleSectionLeft']
        else:
            style = TSTYLES['TitleSectionRight']

        Table.__init__(self,
                       data=self.sections,
                       colWidths=self.col_width,
                       rowHeights=self.row_heights,
                       style=style,
                       hAlign='left',
                       **kwargs)

    @property
    def row_heights(self) -> list[float]:
        if self.__row_heights == []:
            self.__calc_sizes()

        return self.__row_heights

    @property
    def col_width(self) -> float:
        if self.__col_width is None:
            self.__calc_sizes()

        return self.__col_width

    @property
    def sections(self) -> list[list[TitleSection]]:
        offset_cells = [''] * len(self.__sections)
        sections_zip = zip(self.__sections, offset_cells)
        sections = [item for pair in sections_zip for item in pair]
        return [[section] for section in sections]

    def __calc_sizes(self) -> None:
        """Calculates the column widths and row heights required
        for this flowable.

        Sets the private instance variables accordingly.
        """

        col_widths: list[float] = []
        row_heights: list[float] = []
        for section in self.__sections:
            width, height = section.wrap()
            col_widths.append(width)
            row_heights.append(height)

        offset_heights = [self.offset_height] * len(self.__sections)
        heights_zip = zip(row_heights, offset_heights)
        self.__row_heights = [item for pair in heights_zip for item in pair]
        self.__col_width = max(col_widths)


class TitleSectionContainer(Table):
    """Container for one or more columns of title sections."""

    def __init__(self, sections: list[list[TitleSection]], **kwargs):
        if sections == []:
            raise SummaryGenError('Invalid Data: at least one section'
                                  ' column is required to generate a'
                                  ' container.')

        sub_containers: list[TitleSectionSubContainer] = []
        for i, section in enumerate(sections):
            if i == 0:
                side = 'left'
            else:
                side = 'right'
            sub_containers.append(TitleSectionSubContainer(section, side))

        self.total_height = max([
            math.fsum(container.row_heights) for container in sub_containers
        ])
        col_widths = [INNER_WIDTH / len(sub_containers)] * len(sub_containers)
        Table.__init__(self,
                       data=[sub_containers],
                       colWidths=col_widths,
                       style=TSTYLES['TitleSectionContainer'],
                       **kwargs)


class TitlePage(KeepTogether):
    """A measure title page.

    Each measure within the summary should be preceded by a
    title page.

    Guaranteed to take up a full page.
    """

    def __init__(self, measure: Measure, **kwargs):
        if kwargs.get('normalizedData', None) is not None:
            Table.__init__(self, measure, **kwargs)
            return

        self.measure = measure
        self.data: list[Flowable] = []
        self.row_heights: list[Flowable] = []

        img_path = utils.asset_path('etrm.png', 'images')
        img = utils.get_rlimage(img_path,
                                INNER_WIDTH / 9,
                                INNER_HEIGHT / 3,
                                hAlign='LEFT')
        self.row_heights.append(img.drawHeight)
        self.data.append(img)

        self.add_text('MEASURE CHARACTERIZATION', PSTYLES['TitlePageSubtitle'])
        self.add_spacer(0.15 * inch)
        self.add_text(measure.name, PSTYLES['TitlePageTitle'])
        self.add_spacer(_NL_HEIGHT)

        link = measure.link
        link_xml = f'<link href=\"{link}\">{link}/</link>'
        self.add_text(link_xml, PSTYLES['TitleLink'])

        self.data.append(self.sections)
        self.row_heights.append(self.sections.total_height)

        rem_height = INNER_HEIGHT - math.fsum(self.row_heights)
        self.insert_spacer(1, rem_height / 2)
        self.insert_spacer(-1, rem_height / 2)
        table = Table([[item] for item in self.data],
                      colWidths=INNER_WIDTH,
                      rowHeights=self.row_heights,
                      style=TSTYLES['TitlePage'])
        KeepTogether.__init__(self, [table])

    @property
    def sections(self) -> TitleSectionContainer:
        try:
            return self.__sections
        except AttributeError:
            self.__sections = self.__build_sections_container(self.measure)
            return self.__sections

    def __build_sections_container(self,
                                   measure: Measure
                                  ) -> TitleSectionContainer:
        use_category = measure.use_category.upper()
        uc_title = lookups.USE_CATEGORIES[use_category]
        uc_section = TitleSection('USE CATEGORY',
                                  f'{use_category} - {uc_title}',
                                  side='left')

        pa_section = TitleSection('PA LEAD',
                                  measure.pa_lead,
                                  side='left')

        version_section = TitleSection('VERSION',
                                       measure.full_version_id,
                                       side='left')

        start_section = TitleSection('EFFECTIVE START DATE',
                                     measure.effective_start_date,
                                     side='right')

        end_section = TitleSection('END DATE',
                                   measure.sunset_date or '',
                                   side='right')

        if _SYSTEM == 'Windows':
            fmt = '#'
        else:
            fmt = '-'
        download_date = _NOW.strftime(rf'%B %{fmt}d, %Y %{fmt}I:%M%p')
        download_section = TitleSection('DOWNLOADED',
                                          download_date,
                                          side='right')        

        sections = [
            [uc_section, pa_section, version_section],
            [start_section, end_section, download_section]
        ]
        return TitleSectionContainer(sections)

    def add_text(self, text: str, style: ParagraphStyle) -> None:
        used_height = math.fsum(self.row_heights) + self.sections.total_height
        para = Paragraph(text, style)
        _, h = para.wrap(INNER_WIDTH, INNER_HEIGHT - used_height)
        self.data.append(para)
        self.row_heights.append(h)

    def add_spacer(self, height: float) -> None:
        self.data.append(Spacer(1, height))
        self.row_heights.append(height)

    def insert_spacer(self, index: int, height: float) -> None:
        self.data.insert(index, Spacer(1, height))
        self.row_heights.insert(index, height)


class Reference(Flowable):
    """A custom flowable that draws an eTRM reference tag."""

    def __init__(self,
                 text: str,
                 link: str | None=None,
                 style: ParagraphStyle | None=None):
        self.text = text
        self.link = link
        self.tri_frac = 0.25
        self.rect_frac = 1 - self.tri_frac
        self.base_style = PSTYLES['ReferenceTag']
        self.x_padding = self.base_style.x_padding
        self.y_padding = self.base_style.y_padding
        self.__height = self.base_style.leading + self.y_padding
        font_size = self.__height * self.rect_frac - self.y_padding
        self.style = copy.deepcopy(self.base_style)
        self.style.font_size = font_size
        text_width = stringWidth(self.text,
                                 self.base_style.font_name,
                                 self.base_style.font_size)
        small_width = stringWidth(self.text,
                                  self.style.font_name,
                                  self.style.font_size)
        self.text_offset = text_width - small_width + self.x_padding
        self.__width = text_width + self.x_padding

    def wrap(self, *args) -> tuple[float, float]:
        return (self.__width, self.__height)

    def draw(self):
        canvas = self.canv
        if not isinstance(canvas, Canvas):
            return

        bg_color = COLORS['ReferenceTagBG']
        rect_height = self.__height * self.rect_frac
        y = self.__height - rect_height

        canvas.saveState()
        try:
            canvas.setFillColor(bg_color)

            tri_path = canvas.beginPath()
            assert isinstance(tri_path, PDFPathObject)

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

            text_obj = canvas.beginText(x=self.text_offset / 2,
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
                        self.__width,
                        self.__height)
                canvas.linkURL(url=self.link,
                               rect=area,
                               relative=1)
        finally:
            canvas.restoreState()


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
                  style: ParagraphStyle | None=None,
                  strict: bool=False
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
                    if elem.width > max_width and strict:
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
                    elif elem.width <= max_width:
                        element_lines.append(current_line)
                        current_line = ElementLine(max_width=max_width,
                                                   style=style)
                        current_line.add(elem)
                    else:
                        current_line.max_width = None
                        current_line.add(elem)
                        element_lines.append(current_line)
                        current_line = ElementLine(max_width=max_width,
                                                   style=style)
    if len(current_line) != 0:
        element_lines.append(current_line)
    return element_lines


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


_TABLE_STYLES = list[ParagraphStyle] | ParagraphStyle


class BasicTable(Table):
    """Base class for tables in the summary PDF.

    Use when creating a new table or extend to create a new
    table class.

    Do not use when creating a new class that will extend the
    `Table` class, but will not be a genuine table.

    Apologies for the __init__ weirdness here, but we must appease
    the ReportLab gods.
    """

    def __init__(self,
                 data: list[list[str | ElementLine]],
                 headers: int=1,
                 measure: Measure | None=None,
                 spans: list[_TABLE_SPAN] | None=None,
                 header_orient: _TABLE_ORIENT='top',
                 header_styles: _TABLE_STYLES=PSTYLES['ValueTableHeader'],
                 body_styles: _TABLE_STYLES=PSTYLES['ValueTableDeterminant'],
                 table_style: TableStyle | None=None,
                 col_widths: list[float] | float | None=None,
                 row_heights: list[float] | float | None=None,
                 h_align: Literal['left', 'center', 'right']='left',
                 repeat_rows: int=1,
                 **kwargs):
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

        if kwargs.get('normalizedData') is not None:
            Table.__init__(self, data, **kwargs)
            return

        assert data != []
        row_len: float | None = None
        for row in data:
            if row_len is None:
                row_len = len(row)
            else:
                assert len(row) == row_len
        assert row_len is not None

        self.header_orient = header_orient
        self.measure = measure
        self.max_width = INNER_WIDTH
        self.spans = spans or []
        self.span_dict = {str((y, x)): span_sizes
                            for (y, x), span_sizes in self.spans}

        self.style = table_style or get_table_style(data=data,
                                                    headers=headers,
                                                    determinants=row_len,
                                                    spans=self.spans)
        self.h_padding = self.style.left_padding + self.style.right_padding
        self.v_padding = self.style.top_padding + self.style.bottom_padding

        style_count = row_len if header_orient == 'top' else len(data)
        if isinstance(header_styles, ParagraphStyle):
            self.header_styles = [header_styles] * style_count
        else:
            assert len(header_styles) == headers
            self.header_styles = header_styles

        if isinstance(body_styles, ParagraphStyle):
            self.body_styles = [body_styles] * style_count
        else:
            assert len(body_styles) == style_count
            self.body_styles = body_styles

        assert headers > -1
        self.header_count = headers
        self.data = self.__sanitize_data(data)

        if isinstance(col_widths, float):
            self.__col_widths = [col_widths] * row_len
        else:
            if col_widths is not None:
                assert row_len == len(col_widths)
            self.__col_widths = col_widths

        if isinstance(row_heights, float):
            self.__row_heights = [row_heights] * len(data)
        else:
            if row_heights is not None:
                assert len(data) == len(row_heights)
            self.__row_heights = row_heights

        self.table_cells = self.__convert_data(self.data)
        if header_orient == 'left':
            columns = utils.rotate_matrix(self.table_cells)
            self.headers = columns[0:headers]
        else:
            self.headers = self.table_cells[0:headers]

        Table.__init__(self,
                       data=self.table_cells,
                       colWidths=self.col_widths,
                       rowHeights=self.row_heights,
                       style=self.style,
                       hAlign=h_align.upper(),
                       repeatRows=repeat_rows,
                       **kwargs)

    @property
    def col_widths(self) -> list[float]:
        if self.__col_widths is not None:
            return self.__col_widths

        col_widths = self.__calc_col_widths(self.data)
        widths_len = len(col_widths)
        for y, row in enumerate(self.data):
            try:
                assert len(row) == widths_len
            except AssertionError as err:
                raise SummaryGenError(
                    f'the number of column widths {widths_len} does not'
                    f' match the amount of columns in row {y}'
                ) from err
        self.__col_widths = col_widths
        return self.__col_widths

    @property
    def row_heights(self) -> list[float]:
        if self.__row_heights is not None:
            return self.__row_heights

        row_heights = self.__calc_row_heights(self.data)
        rows = [row for row in zip(*self.data)]
        heights_len = len(row_heights)
        for x, col in enumerate(rows):
            try:
                assert len(col) == heights_len
            except AssertionError as err:
                raise SummaryGenError(
                    f'the number of row heights {heights_len} does not'
                    f' match the amount of rows in column {x}'
                ) from err
        self.__row_heights = row_heights
        return self.__row_heights

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

    def __calc_min_widths(self,
                          data: list[list[ElementLine]],
                          size: int=1
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

        return [max(column)
                    for column
                    in utils.rotate_matrix(min_matrix)]

    def __calc_col_widths(self, data: list[list[ElementLine]]) -> list[float]:
        """Returns the list of column widths for this table.

        Column widths are calculated by unwrapping data until it cannot
        unwrap without exceeding the max width.

        This method directly joins previously split elements, avoiding the
        costly `wrap_elements` method.
        """

        size = 1
        prev_widths = self.__calc_min_widths(data, size)
        while math.fsum(prev_widths) <= self.max_width:
            col_widths = self.__calc_min_widths(data, size=size + 1)
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

    def __calc_row_heights(self,
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

    def __sanitize_data(self,
                        data: list[list[ElementLine | str]]
                       ) -> list[list[ElementLine]]:
        sanitized_data: list[list[ElementLine]] = []
        for y, row in enumerate(data):
            sanitized_row: list[ElementLine] = []
            for x, cell in enumerate(row):
                if isinstance(cell, str):
                    style = self.get_style(x, y)
                    elem = ElementLine(string=cell,
                                       style=style,
                                       max_width=None)
                else:
                    elem = cell
                sanitized_row.append(elem)
            sanitized_data.append(sanitized_row)
        return sanitized_data

    def __wrap_data(self,
                    data: list[list[ElementLine]]
                   ) -> list[list[list[ElementLine]]]:
        h_padding = self.style.left_padding + self.style.right_padding
        cell_widths = [math.ceil(width - h_padding)
                        for width in self.col_widths]
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
                frag_line.append(wrap_elements(elem_line.elements,
                                               max_width=cell_width))
            frags.append(frag_line)
        return frags

    def __convert_data(self,
                       data: list[list[ElementLine]]
                      ) -> list[list[TableCell | str]]:
        frags = self.__wrap_data(data)
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
                 spans: list[_TABLE_SPAN] | None=None,
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
                                               type=ElemType.REF,
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


class BulletList(Table):
    def __init__(self,
                 element_matrix: list[list[ParagraphElement]],
                 measure: Measure | None=None,
                 bullet_indent: float=11,
                 text_indent: float=11,
                 item_spacing: float=20,
                 **kwargs):
        if kwargs.get('normalizedData', None) is not None:
            Table.__init__(self, element_matrix, **kwargs)
            return

        if measure is None:
            raise SummaryGenError('An eTRM measure is required to generate'
                                  ' a summary bullet list')

        self.bullet_indent = bullet_indent
        self.text_indent = text_indent

        bullet_style = PSTYLES['BulletPoint']
        bullet = Paragraph(u'\u25a0', style=bullet_style) # square
        bullet_width = stringWidth(bullet.text,
                                   bullet_style.font_name,
                                   bullet_style.font_size)

        text_width = INNER_WIDTH - bullet_width
        text_width -= self.bullet_indent + self.text_indent
        self.text_width = text_width

        items: list[SummaryParagraph] = []
        for elements in element_matrix:
            element = SummaryParagraph(elements,
                                       measure,
                                       max_width=self.text_width)
            items.append(element)
        row_heights = [math.fsum(row._argH) for row in items]

        bullet.wrap(bullet_width, max(row_heights))
        bullet_spacer = Spacer(width=self.bullet_indent,
                               height=min(row_heights))
        text_spacer = Spacer(width=self.text_indent,
                             height=min(row_heights))

        data: list[list[Paragraph | SummaryParagraph | Spacer]] = []
        for item in items:
            data.append([bullet_spacer, bullet, text_spacer, item])

        col_widths = [
            self.bullet_indent,
            bullet_width,
            self.text_indent,
            self.text_width
        ]
        spacer_row: list[Spacer] = []
        for col_width in col_widths:
            spacer_row.append(Spacer(width=col_width, height=item_spacing))
        spacer_matrix = [spacer_row] * len(data)
        data = [list(item) for pair
                    in zip(data, spacer_matrix)
                    for item in pair]
        data.pop()

        spacer_heights = [item_spacing] * len(data)
        row_heights = [item for pair
                        in zip(row_heights, spacer_heights)
                        for item in pair]
        row_heights.pop()
        Table.__init__(self,
                       data=data,
                       colWidths=col_widths,
                       rowHeights=row_heights,
                       hAlign='LEFT',
                       style=TSTYLES['SummaryList'])
