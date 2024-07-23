import copy
import math
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfgen.pathobject import PDFPathObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Spacer as _Spacer,
    Flowable,
    Paragraph,
    Table
)

from src.etrm.models import Measure
from src.summarygen.styles import (
    ParagraphStyle,
    PSTYLES,
    TSTYLES,
    COLORS,
    INNER_WIDTH,
    _NL_HEIGHT
)
from src.summarygen.rlobjects import (
    ParagraphElement
)
from src.summarygen.flowables.paragraph import SummaryParagraph
from src.summarygen.exceptions import SummaryGenError


class Spacer(_Spacer):
    """Overwrites the ReportLab `Spacer` class to shrink in order
    to not exceed frame heights.
    """

    def wrap(self, availWidth, availHeight):
        height = min(self.height, availHeight - 1e-8)
        return (availWidth, height)


NEWLINE = Spacer(1, _NL_HEIGHT, isGlue=True)


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
