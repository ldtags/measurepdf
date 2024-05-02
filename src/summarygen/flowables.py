from bs4 import BeautifulSoup, PageElement, NavigableString, Tag
from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas, PDFTextObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, Table

from src.etrm import API_URL
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


def _parse_element(element: PageElement) -> list[ParagraphElement]:
    if isinstance(element, NavigableString):
        return [ParagraphElement(element.get_text())]

    if not isinstance(element, Tag):
        raise RuntimeError(f'unsupported page element: {element}')

    match element.name:
        case 'p':
            return _parse_elements(element.contents)
        case 'div' | 'span':
            json_str = element.attrs.get('data-etrmreference', None)
            if json_str != None:
                return [ReferenceTag(json_str)]
            else:
                return _parse_elements(element.contents)
        case 'strong' | 'sup' | 'sub':
            elements = _parse_elements(element.contents)
            for item in elements:
                style = TextStyle(element.name)
                if style not in item.styles:
                    item.styles.append(style)
            return elements


def _parse_elements(elements: list[PageElement]) -> list[ParagraphElement]:
    contents: list[ParagraphElement] = []
    for element in elements:
        parsed_elements = _parse_element(element)
        if parsed_elements != None:
            contents.extend(parsed_elements)
    return contents


def _parse_paragraph(source: str | Tag) -> list[ParagraphElement]:
    if isinstance(source, Tag):
        contents = _parse_element(source)
    elif isinstance(source, str):
        soup = BeautifulSoup(source, 'html.parser')
        contents = _parse_elements(soup.find_all(recursive=False))
    else:
        raise RuntimeError(f'unsupported paragraph source type: {type(source)}')
    return contents


class SummaryParagraph(Flowable):
    def __init__(self,
                 x: int=0,
                 y: int=0,
                 html: str='',
                 element: Tag | None=None):
        Flowable.__init__(self)
        self.x = x
        self.y = y
        self._elements = _parse_paragraph(element or html)
        self.style = PSTYLES['Paragraph']
        self.font_name = str(self.style.attrs['fontName'])
        self.font_size = float(self.style.attrs['fontSize'])
        self.leading = float(self.style.attrs.get('leading',
                                                  self.font_size * 1.2))

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
                    element.text = element.text.replace(line, '').strip()
            elif j != word_count + 1:
                line = ' '.join(words[0:(j - 1)])
                _element_line.append(element.copy(text=line))
                _element_lines.append(_element_line)
                _element_line = []
                cur_width = 0
                element.text = element.text.replace(line, '').strip()
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
        canvas.setFillColor(COLORS['ReferenceTagBG'])
        canvas.rect(x + x_pad,
                    y - (self.leading - self.font_size) + 0.25,
                    str_width - 4.5 + w_pad,
                    self.font_size,
                    stroke=0,
                    fill=1)
        canvas.setFillColor(colors.black)
        x, _ = text_obj.getCursor()
        text_obj.moveCursor(x + space_width / 2, 0)

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


class Reference(Paragraph):
    def __init__(self, measure: Measure, tag: ReferenceTag):
        statewide_id, version_id = measure.full_version_id.split('-', 1)
        link = '/'.join([API_URL, statewide_id, version_id])
        text = f'<link href=\"{link}\">{tag.text}</link>'
        Paragraph.__init__(self, text=text, style=PSTYLES['ReferenceTag'])


class ValueTableHeader(Paragraph):
    def __init__(self, text: str, link: str | None=None):
        header_text = text
        if link != None:
            header_text = f'<link href=\"{link}\">{header_text}</link>'
        Paragraph.__init__(self, text, style=PSTYLES['h6'])


class EmbeddedValueTable(Table):
    def __init__(self, measure: Measure, tag: EmbeddedValueTableTag):
        self.style = value_table_style(data, embedded=True)
        api_name = tag.obj_info.api_name_unique
        table = measure.get_value_table(api_name)
        if table == None:
            raise SummaryGenError(f'value table {api_name} does not exist'
                                    + f' in {measure.full_version_id}')
        column_indexes: list[int] = 0
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
        data = [headers].extend(body)
        col_widths: list[float] = []
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
                       style=self.style)

    def _col_width(self, text: str) -> float:
        text_width = stringWidth(text,
                                 self.style.font_name,
                                 self.style.font_size)
        return self.style.left_padding + text_width + self.style.right_padding

    def _row_height(self) -> float:
        padding = self.style.top_padding + self.style.bottom_padding
        return self.style.font_size + padding
