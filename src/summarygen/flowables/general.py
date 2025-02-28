import copy
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfgen.pathobject import PDFPathObject
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Spacer as _Spacer,
    Flowable
)

from src import assets
from src.summarygen import utils
from src.summarygen.styles import (
    ParagraphStyle,
    PSTYLES,
    COLORS,
    NL_HEIGHT
)


class Spacer(_Spacer):
    """Overwrites the ReportLab `Spacer` class to shrink in order
    to not exceed frame heights.
    """

    def wrap(self, availWidth, availHeight):
        height = min(self.height, availHeight - 1e-8)
        return (availWidth, height)


NEWLINE = Spacer(1, NL_HEIGHT, isGlue=True)


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


class StreamlinedPermutations(Flowable):
    def __init__(self, text: str, link: str) -> None:
        self.text = text
        self.link = link

        self.img_path = assets.get_path("images/excel_icon.png")
        self.img_obj = utils.get_image(
            self.img_path,
            max_height=0.3 * inch
        )
        self._style = style = PSTYLES["SmallerBase"]
        text_width = stringWidth(text, style.font_name, style.font_size)
        self._width = max(text_width, self.img_obj.drawWidth)
        self._height = self.img_obj.drawHeight + style.leading

    def wrap(self, *args) -> tuple[float, float]:
        return (self._width, self._height)

    def draw(self) -> None:
        canvas = self.canv
        if not isinstance(canvas, Canvas):
            return

        canvas.saveState()
        try:
            text_obj = canvas.beginText(x=0, y=0)
            text_obj.setFont(
                self._style.font_name,
                self._style.font_size,
                self._style.leading
            )
            text_obj.setFillColor(self._style.text_color)
            text_obj.textOut(self.text)
            canvas.drawText(text_obj)

            rem_width = self._width - self.img_obj.drawWidth
            canvas.drawImage(
                self.img_path,
                x=rem_width / 2,
                y=self._style.leading,
                height=self.img_obj.drawHeight,
                width=self.img_obj.drawWidth,
                preserveAspectRatio=True,
                mask="auto"
            )

            canvas.linkURL(
                url=self.link,
                rect=(0, -3, self._width, self._height),
                relative=1
            )
        finally:
            canvas.restoreState()
