import unicodedata
from bs4 import BeautifulSoup, PageElement, NavigableString, Tag, ResultSet
from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas, PDFTextObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    ListFlowable,
    ListItem
)

from src.etrm import ETRM_URL
from src.etrm.models import Measure
from src.exceptions import SummaryGenError
from src.summarygen.models import (
    ParagraphElement,
    ReferenceTag,
    EmbeddedValueTableTag,
    ElemType,
    TextStyle
)
from src.summarygen.styling import PSTYLES, COLORS, value_table_style
from src.summarygen.rlobjects import BetterParagraphStyle, BetterTableStyle


def _parse_element(element: PageElement) -> list[ParagraphElement]:
    if isinstance(element, NavigableString):
        return [ParagraphElement(element.get_text())]

    if not isinstance(element, Tag):
        raise RuntimeError(f'unsupported page element: {element}')

    match element.name:
        case 'p':
            # add newline here instead of during flowable addition
            # this will account for nested paragraphs (ugh)
            elements = _parse_elements(element.contents)
            return elements
        case 'th' | 'td' | 'li':
            return _parse_elements(element.contents)
        case 'div' | 'span':
            json_str = element.attrs.get('data-etrmreference', None)
            if json_str != None:
                return [ReferenceTag(json_str)]
            return _parse_elements(element.contents)
        case 'strong' | 'sup' | 'sub':
            elements = _parse_elements(element.contents)
            for item in elements:
                style = TextStyle(element.name)
                if style not in item.styles:
                    item.styles.append(style)
            return elements
        case _:
            raise RuntimeError(f'unsupported tag: {element.name}')


def _parse_elements(elements: list[PageElement]) -> list[ParagraphElement]:
    contents: list[ParagraphElement] = []
    for element in elements:
        parsed_elements = _parse_element(element)
        if parsed_elements != None:
            contents.extend(parsed_elements)
    return contents


class SummaryParagraph(Flowable):
    # TODO: add option to set the height and width of the element (for wrapping)
    def __init__(self,
                 x: int=0,
                 y: int=0,
                 text: str='',
                 html: str | None=None,
                 element: PageElement | None=None,
                 elements: list[PageElement] | None=None,
                 paragraph_element: ParagraphElement | None=None,
                 paragraph_elements: list[ParagraphElement] | None=None,
                 style: BetterParagraphStyle | None=None):
        Flowable.__init__(self)
        self.x = x
        self.y = y
        self._elements: list[ParagraphElement] = []
        if paragraph_elements != None:
            self._elements = paragraph_elements
        elif paragraph_element != None:
            self._elements = [paragraph_element]
        elif elements != None:
            for _element in elements:
                self._elements.extend(_parse_element(_element))
        elif element != None:
            self._elements = _parse_element(element)
        elif html != None:
            soup = BeautifulSoup(html, 'html.parser')
            self._elements = _parse_elements(soup.find_all(recursive=False))
        else:
            self._elements = [ParagraphElement(text)]
        if style != None:
            self.style = style
        else:
            self.style = PSTYLES['Paragraph']
        self._join_elements()
        self.font_name = str(self.style.attrs['fontName'])
        self.font_size = float(self.style.attrs['fontSize'])
        self.leading = float(self.style.attrs.get('leading',
                                                  self.font_size * 1.2))

    def _join_elements(self):
        sections: list[tuple[int, int]] = []
        start = -1
        cur_styles: list[TextStyle] = []
        cur_type: ElemType | None = None
        for i, element in enumerate(self._elements):
            if start == -1:
                if i == len(self._elements) - 1:
                    sections.append((i, i))
                else:
                    start = i
                    cur_styles = element.styles
                    cur_type = element.type
            elif element.styles != cur_styles or element.type != cur_type:
                sections.append((start, i - 1))
                if i == len(self._elements) - 1:
                    sections.append((i, i))
                else:
                    start = i
                    cur_styles = element.styles
                    cur_type = element.type
            elif i == len(self._elements) - 1:
                sections.append((start, i))

        elements: list[ParagraphElement] = []
        for start, end in sections:
            element: ParagraphElement | None = None
            for i in range(start, end + 1):
                if element == None:
                    element = self._elements[i]
                else:
                    element.text += self._elements[i].text
            elements.append(element)
        self._elements = elements

    @property
    def text(self) -> str:
        return ''.join([item.text for item in self._elements])

    @property
    def element_lines(self) -> list[list[ParagraphElement]]:
        elements = self._elements
        _element_lines: list[list[ParagraphElement]] = []
        _element_line: list[ParagraphElement] = []
        i = 0
        cur_width = 0
        while i < len(elements):
            element = elements[i]
            font_name = self.font_name
            if TextStyle.STRONG in element.styles:
                font_name += 'B'
            words = element.text.strip().split(' ')
            word_count = len(words)
            line = ''
            j = 1
            while j < word_count + 1:
                line = ' '.join(words[0:j])
                line_width = cur_width + self._string_width(line, font_name)
                if line_width > self.width:
                    break
                j += 1
            if j == 1:
                _element_lines.append(_element_line)
                _element_line = []
                cur_width = 0
                if self._string_width(line, font_name) > self.width:
                    _element_lines.append([element.copy(text=line)])
                    element.text = element.text.replace(line, '')
            elif j != word_count + 1:
                line = ' '.join(words[0:(j - 1)])
                _element_line.append(element.copy(text=line))
                _element_lines.append(_element_line)
                _element_line = []
                cur_width = 0
                element.text = element.text.replace(line, '')
            else:
                if _element_line == [] and isinstance(element, ReferenceTag):
                    element.text = element.text.lstrip()
                _element_line.append(element)
                cur_width += self._string_width(element.text, font_name)
                i += 1
        if _element_line != []:
            _element_lines.append(_element_line)
        return _element_lines

    def wrap(self, availWidth, availHeight) -> tuple[float, float]:
        para = Paragraph(self.text, style=self.style)
        self.width, self.height = para.wrap(availWidth, availHeight)
        return self.width, self.height

    def _string_width(self, text: str, alt_font: str | None=None) -> float:
        return stringWidth(text, alt_font or self.font_name, self.font_size)

    def _split_text(self, text: str) -> list[str]:
        return simpleSplit(text,
                           self.font_name,
                           self.font_size,
                           self.width)

    def _set_elem_text(self,
                       text_obj: PDFTextObject,
                       element: ParagraphElement):
        text_obj.setFillColor(colors.black)
        font_name = self.font_name
        if TextStyle.STRONG in element.styles:
            font_name += 'B'
        font_size = self.font_size
        if TextStyle.SUP in element.styles or TextStyle.SUB in element.styles:
            font_size = 8
        text_obj.setFont(font_name, font_size)

        rise = 0
        if TextStyle.SUP in element.styles:
            rise += 4
        if TextStyle.SUB in element.styles:
            rise -= 4
        text_obj.setRise(rise)

        for line in self._split_text(element.text):
            x, _ = text_obj.getCursor()
            str_width = self._string_width(line, font_name)
            if x + str_width > self.width:
                text_obj.moveCursor(self.x - x, 0)
            text_obj.textOut(line)

        text_obj.setFont(self.font_name, self.font_size)
        text_obj.setRise(0)

    def _set_ref_text(self, text_obj: PDFTextObject, reference: ReferenceTag):
        font_name = self.font_name + 'B'
        text_obj.setFont(font_name, self.font_size)
        text_obj.setFillColor(colors.white)
        text = reference.text
        space_width = self._string_width(' ', 'SourceSansProB')
        x_pad = -0.25
        w_pad = space_width
        if text[0] == ' ':
            x_pad = space_width
            w_pad = -0.25
        x, _ = text_obj.getCursor()
        str_width = self._string_width(text, font_name)
        if x + str_width > self.width:
            text_obj.moveCursor(self.x - x + x_pad + w_pad / 2, 0)
        x, y = text_obj.getCursor()
        text_obj.textOut(text)
        text_obj.setFillColor(colors.black)
        text_obj.setFont(self.font_name, self.font_size)

        canvas: Canvas = self.canv
        rect_width = str_width - 4.5 + w_pad
        canvas.setFillColor(COLORS['ReferenceTagBG'])
        canvas.rect(x + x_pad,
                    y - (self.leading - self.font_size) + 0.25,
                    rect_width,
                    self.font_size,
                    stroke=0,
                    fill=1)
        canvas.setFillColor(colors.black)
        text_obj.moveCursor(x_pad + rect_width + space_width, 0)

    def draw(self):
        canvas: Canvas = self.canv
        element_lines = self.element_lines
        x = self.x
        y = self.y + self.height - (self.leading - self.font_size) * 4
        for element_line in element_lines:
            for element in element_line:
                text_obj = canvas.beginText()
                text_obj.setTextOrigin(x, y)
                match element.type:
                    case ElemType.TEXT:
                        self._set_elem_text(text_obj, element)
                    case ElemType.REF:
                        self._set_ref_text(text_obj, element)
                canvas.drawText(text_obj)
                x, y = text_obj.getCursor()
            text_obj = canvas.beginText()
            text_obj.setTextOrigin(x, y)
            text_obj.setFont(self.font_name, self.font_size)
            text_obj.textLine()
            canvas.drawText(text_obj)
            x, y = text_obj.getCursor()


def _parse_table_headers(table: Tag) -> list[SummaryParagraph]:
    thead = table.find('thead')
    raw_headers: ResultSet[Tag] = []
    if thead == None:
        raw_headers = table.find_all('th')
    elif isinstance(thead, Tag):
        raw_headers = thead.find_all('th')
    else:
        raise SummaryGenError('missing table headers')
    headers: list[SummaryParagraph] = []
    for raw_header in raw_headers:
        header_elements = _parse_element(raw_header)
        headers.append(SummaryParagraph(paragraph_elements=header_elements))
    return headers


def _parse_table_body(table: Tag) -> list[list[SummaryParagraph]]:
    tbody = table.find('tbody')
    if not isinstance(tbody, Tag):
        raise SummaryGenError('missing table body')
    raw_rows: ResultSet[Tag] = tbody.find_all('tr')
    body_rows: list[list[SummaryParagraph]] = []
    for raw_row in raw_rows:
        raw_cells: ResultSet[Tag] = raw_row.find_all('td')
        cells: list[SummaryParagraph] = []
        for raw_cell in raw_cells:
            cell_elements = _parse_element(raw_cell)
            cells.append(SummaryParagraph(paragraph_elements=cell_elements))
        body_rows.append(cells)
    return body_rows


def _parse_table(table: Tag) -> list[list[SummaryParagraph]]:
    headers = _parse_table_headers(table)
    body = _parse_table_body(table)
    data: list[list[SummaryParagraph]] = []
    data.append(headers)
    data.extend(body)
    return data


class StaticValueTable(Table):
    def __init__(self,
                 x: int=0,
                 y: int=0,
                 html: str='',
                 element: Tag | None=None,
                 data: list[list[str]] | None=None,
                 style: BetterTableStyle | None=None):
        Flowable.__init__(self)
        self.x = x
        self.y = y
        self.data: list[list[SummaryParagraph]] = []
        if data != None:
            self.data = data
        elif element != None:
            self.data = _parse_table(element)
        else:
            self.data = _parse_table(Tag(BeautifulSoup(html)))
        self.style = style or value_table_style(self.data)
        super().__init__(self.data,
                         colWidths=self.col_widths(),
                         rowHeights=self.row_heights(),
                         style=self.style,
                         hAlign='LEFT')

    def _col_width(self, element: SummaryParagraph) -> float:
        padding = self.style.left_padding + self.style.right_padding
        return element.width + padding

    def col_widths(self) -> list[float]:
        if self.data == []:
            return []
        headers = self.data[0]
        col_widths: list[float] = list(range(len(headers)))
        for i in range(len(headers)):
            max_width = 0
            for j in range(len(self.data)):
                col_width = self._col_width(self.data[j][i])
                if col_width > max_width:
                    max_width = col_width
            col_widths[i] = max_width
        return col_widths

    def _row_height(self, element: SummaryParagraph) -> float:
        padding = self.style.top_padding + self.style.bottom_padding
        return element.height + padding

    def row_heights(self) -> list[float]:
        row_heights: list[float] = list(range(len(self.data)))
        for i in range(len(self.data)):
            max_height = 0
            for cell in self.data[i]:
                cell_height = self._row_height(cell)
                if cell_height > max_height:
                    max_height = cell_height
            row_heights[i] = max_height
        return row_heights
                


def _parse_list(ul: Tag) -> list[ListItem]:
    list_items: list[ListItem] = []
    li_list: ResultSet[Tag] = ul.find_all('li')
    for li in li_list:
        items = _parse_element(li)
        for item in items:
            element = SummaryParagraph(paragraph_element=item)
            list_items.append(ListItem(element))

    return list_items


class SummaryList(ListFlowable):
    def __init__(self,
                 html: str='',
                 element: Tag | None=None,
                 style: BetterParagraphStyle | None=None):
        self.list_items: list[ListItem] = []
        if element != None:
            self.list_items = _parse_list(element)
        else:
            list_element = Tag(BeautifulSoup(html, 'html.parser'))
            self.list_items = _parse_list(list_element)
        ListFlowable.__init__(self,
                              self.list_items,
                              start='square',
                              style=style)


class Reference(Paragraph):
    def __init__(self, measure: Measure, tag: ReferenceTag):
        statewide_id, version_id = measure.full_version_id.split('-', 1)
        link = '/'.join([ETRM_URL, statewide_id, version_id])
        text = f'<link href=\"{link}\">{tag.text}</link>'
        Paragraph.__init__(self, text=text, style=PSTYLES['ReferenceTag'])


class ValueTableHeader(Paragraph):
    def __init__(self, text: str, link: str | None=None):
        header_text = text
        if link != None:
            header_text = f'<link href=\"{link}\">{header_text}</link>'
            style = PSTYLES['h6Link']
        else:
            style = PSTYLES['h6']
        Paragraph.__init__(self, header_text, style=style)


class EmbeddedValueTable(Table):
    def __init__(self, measure: Measure, tag: EmbeddedValueTableTag):
        api_name = tag.obj_info.api_name_unique
        table = measure.get_value_table(api_name)
        if table == None:
            raise SummaryGenError(f'value table {api_name} does not exist'
                                    + f' in {measure.full_version_id}')
        column_indexes: list[int] = []
        headers: list[str] = []
        for i, column in enumerate(table.columns):
            if column.api_name in tag.obj_info.vtconf.cids:
                column_indexes.append(i)
                headers.append(column.name)
        body: list[list[str]] = []
        for values_row in table.values:
            row: list[str] = []
            for index in column_indexes:
                row.append(values_row[index])
            body.append(row)
        data = [headers]
        data.extend(body)
        self.style = value_table_style(data, embedded=True)
        col_widths: list[float] = list(range(len(headers)))
        for i in range(len(headers)):
            max_width = 0
            for j in range(len(data)):
                col_width = self._col_width(data[j][i])
                if col_width > max_width:
                    max_width = col_width
            col_widths[i] = max_width
        Table.__init__(self,
                       data,
                       colWidths=col_widths,
                       rowHeights=self._row_height(),
                       style=self.style,
                       hAlign='LEFT')

    def _col_width(self, text: str) -> float:
        text_width = stringWidth(text,
                                 self.style.font_name,
                                 self.style.font_size)
        return self.style.left_padding + text_width + self.style.right_padding

    def _row_height(self) -> float:
        padding = self.style.top_padding + self.style.bottom_padding
        return self.style.font_size + padding
