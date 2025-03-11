import math
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    KeepTogether,
    Table,
    Paragraph,
    Flowable
)

from src import assets, __version__, __date__
from src.summarygen import utils
from src.summarygen.styles import (
    INNER_WIDTH,
    INNER_HEIGHT,
    TSTYLES,
    PSTYLES,
    COLORS
)


class VersionContainer(Flowable):
    def __init__(self, ipadx: float = 8.0, ipady: float = 4.0) -> None:
        self._ipadx = ipadx
        self._ipady = ipady
        self._style = style = PSTYLES["VersionContainer"]
        self._text = f"VERSION {__version__}"
        text_width = stringWidth(self._text, style.font_name, style.font_size)
        self._width = text_width + ipadx * 2
        self._height = style.leading + ipady * 2

    def wrap(self, *args) -> tuple[float, float]:
        return (self._width, self._height)

    def draw(self) -> None:
        canvas = self.canv
        if not isinstance(canvas, Canvas):
            return

        canvas.saveState()
        try:
            canvas.setFillColor(COLORS["LightBlack"])
            canvas.roundRect(0, 0, self._width, self._height, 4, stroke=0, fill=1)
            canvas.restoreState()

            canvas.saveState()
            text_obj = canvas.beginText(self._ipadx, self._ipady * 1.75)
            text_obj.setFont(self._style.font_name, self._style.font_size, self._style.leading)
            text_obj.setFillColor(self._style.text_color)
            text_obj.textOut(self._text)
            canvas.drawText(text_obj)
        finally:
            canvas.restoreState()


class CoverPage(KeepTogether):
    def __init__(self) -> None:
        img_path = assets.get_path("images/etrm.png")
        img_obj = utils.get_image(img_path, max_height=120)
        caption_style = PSTYLES["CoverCaption"].bold
        max_width = 0
        for text in ["California", "Statewide", "Deemed", "Measures"]:
            width = stringWidth(text, caption_style.font_name, caption_style.font_size)
            max_width = max(max_width, width)

        # build top content container (eTRM logo and caption)
        title_obj = Table(
            [
                [Paragraph("California", style=caption_style)],
                [Paragraph("Statewide", style=caption_style)],
                [Paragraph("Deemed", style=caption_style)],
                [Paragraph("Measures", style=caption_style)]
            ],
            hAlign="LEFT",
            style=TSTYLES["CoverCaption"]
        )
        spacer = 10
        top_table = Table(
            [["", img_obj, "", title_obj]],
            colWidths=[
                INNER_WIDTH - max_width - img_obj.drawWidth - spacer,
                img_obj.drawWidth,
                spacer,
                max_width
            ],
            style=TSTYLES["CoverTopContent"]
        )
        data = [[top_table]]
        top_height = max(img_obj.drawHeight, caption_style.leading * 4)

        # Build middle content container (cover page title)
        title_para = Paragraph(
            "Technical Reference Manual for California Municipal Utilities"
                " Association: 2025 First Edition",
            style=PSTYLES["CoverTitle"].bold
        )
        _, mid_height = title_para.wrap(INNER_WIDTH, 0)
        data.append([
            Table(
                [[title_para]],
                style=TSTYLES["CoverMidContent"],
                hAlign="RIGHT"
            )
        ])

        # Build bottom content container (version and last updated date)
        version_container = VersionContainer()
        cpd_style = PSTYLES["CoverPreDate"].italic
        cd_style = PSTYLES["CoverDate"]
        cpd_text = "Last Updated  "
        cpd_width = stringWidth(cpd_text, cpd_style.font_name, cpd_style.font_size)
        cd_width = stringWidth(__date__, cd_style.font_name, cd_style.font_size)
        max_width = cpd_width + cd_width
        date_table = Table(
            [[Paragraph(cpd_text, style=cpd_style.italic), Paragraph(__date__, style=cd_style)]],
            colWidths=(cpd_width, cd_width),
            style=TSTYLES["CoverDateContent"],
            hAlign="RIGHT"
        )
        bottom_content = Table(
            [[version_container], [""], [date_table]],
            style=TSTYLES["CoverBottomContent"],
            colWidths=max_width,
            rowHeights=[version_container._height, 8, PSTYLES["CoverPreDate"].leading],
            hAlign="RIGHT"
        )
        data.append([bottom_content])
        bottom_height = math.fsum(bottom_content._argH)

        # Build content container and apply vertical spacing
        rem_height = INNER_HEIGHT - top_height - mid_height - bottom_height
        data.insert(1, [""])
        data.insert(3, [""])
        super().__init__([
            Table(
                data,
                style=TSTYLES["CoverContent"],
                rowHeights=[
                    top_height,
                    rem_height * (1 / 3),
                    mid_height,
                    rem_height * (2 / 3),
                    bottom_height
                ],
                hAlign="RIGHT"
            )
        ])
