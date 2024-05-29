from __future__ import annotations
from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas, PDFTextObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table
)

from src.etrm import ETRM_URL
from src.etrm.models import Measure
from src.summarygen.models import (
    ParagraphElement,
    ReferenceTag,
    ElemType,
    TextStyle
)
from src.summarygen.styling import PSTYLES, TSTYLES, COLORS
from src.summarygen.rlobjects import BetterParagraphStyle


class SummaryParagraph(Flowable):
    def __init__(self,
                 x: int=0,
                 y: int=0,
                 height: float | None=None,
                 width: float | None=None,
                 text: str='',
                 paragraph_element: ParagraphElement | None=None,
                 paragraph_elements: list[ParagraphElement] | None=None,
                 style: BetterParagraphStyle | None=None,
                 ref_link: str | None=None):
        Flowable.__init__(self)
        self.x = x
        self.y = y
        self.height = height or 0
        self.width = width or 0
        self._elements: list[ParagraphElement] = []
        if paragraph_elements != None:
            self._elements = paragraph_elements
        elif paragraph_element != None:
            self._elements = [paragraph_element]
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
        self.ref_link = ref_link

    def _join_elements(self):
        sections: list[tuple[int, int]] = []
        start = -1
        cur_styles: list[TextStyle] = []
        cur_type: ElemType | None = None
        for i, element in enumerate(self._elements):
            if start == -1:
                if i == len(self._elements) - 1 or element.type == ElemType.REF:
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
            if TextStyle.ITALIC in element.styles:
                font_name += 'I'
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
                if _element_line != []:
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
        self.avail_width = availWidth
        self.avail_height = availHeight
        para = Paragraph(self.text, style=self.style)
        self.width, self.height = para.wrap(availWidth, availHeight)
        return self.width, self.height

    def split(self, availWidth, availHeight) -> list[SummaryParagraph]:
        self.avail_width = availWidth
        self.avail_height = availHeight
        para = Paragraph(self.text, style=self.style)
        paras = para.split(availWidth, availHeight)
        return paras

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
        if TextStyle.ITALIC in element.styles:
            font_name += 'I'
        font_size = self.font_size
        rise = 0
        if TextStyle.SUP in element.styles or TextStyle.SUB in element.styles:
            font_size = 8
            if TextStyle.SUP in element.styles:
                rise = 4
            if TextStyle.SUB in element.styles:
                rise = -4
        text_obj.setFont(font_name, font_size)
        text_obj.setRise(rise)

        x, _ = text_obj.getCursor()
        str_width = self._string_width(element.text, font_name)
        if x + str_width > self.width:
            text_obj.moveCursor(self.x - x, 0)
        text_obj.textOut(element.text.lstrip())

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
        x = x + x_pad
        y = y - (self.leading - self.font_size) + 0.25
        canvas.rect(x,
                    y,
                    rect_width,
                    self.font_size,
                    stroke=0,
                    fill=1)
        if self.ref_link != None:
            canvas.linkURL(self.ref_link,
                           (x, y, x + rect_width, y + self.font_size),
                           relative=1)
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


class ElementLine(Table):
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
