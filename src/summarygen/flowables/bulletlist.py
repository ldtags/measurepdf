import math
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Paragraph,
    Table
)

from src.etrm.models import Measure
from src.summarygen.styles import (
    PSTYLES,
    TSTYLES,
    INNER_WIDTH
)
from src.summarygen.rlobjects import (
    ParagraphElement
)
from src.summarygen.flowables.general import Spacer
from src.summarygen.flowables.paragraph import SummaryParagraph


class BulletOption:
    def __init__(self, bullets: list[str]) -> None:
        self.bullets = bullets

    def get_bullet(self, level: int) -> str:
        if level < 1:
            level = 1

        return self.bullets[(level - 1) % len(self.bullets)]


SQUARE_BULLET = BulletOption([u"\u25a0"])
DASH_BULLET = BulletOption([u"\u2014"])
CIRCLE_BULLET = BulletOption([u"\u25cf", u"\u25cb"])


class BulletList(Table):
    def __init__(
        self,
        element_matrix: list[list[ParagraphElement]],
        measure: Measure | None = None,
        bullet_indent: float = 11,
        text_indent: float = 7,
        item_spacing: float = 0,
        max_width: float = INNER_WIDTH,
        bullet_choice: BulletOption = CIRCLE_BULLET,
        level: int = 1,
        **kwargs
    ) -> None:
        if kwargs.get("normalizedData") is not None:
            super().__init__(element_matrix, **kwargs)
            return

        self.bullet_indent = bullet_indent * level
        self.text_indent = text_indent

        bullet_style = PSTYLES["BulletPoint"]
        bullet = Paragraph(bullet_choice.get_bullet(level), style=bullet_style)
        bullet_width = stringWidth(
            bullet.text,
            bullet_style.font_name,
            bullet_style.font_size
        )

        text_width = max_width - bullet_width
        text_width -= self.bullet_indent + self.text_indent
        self.text_width = text_width

        items: list[SummaryParagraph] = []
        for elements in element_matrix:
            element = SummaryParagraph(elements, measure, max_width=self.text_width)
            items.append(element)

        row_heights = [math.fsum(row._argH) for row in items]
        bullet.wrap(bullet_width, max(row_heights))
        bullet_spacer = Spacer(width=self.bullet_indent, height=min(row_heights))
        text_spacer = Spacer(width=self.text_indent, height=min(row_heights))

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
        data = [
            list(item)
            for pair
            in zip(data, spacer_matrix)
            for item
            in pair
        ]
        data.pop()

        spacer_heights = [item_spacing] * len(data)
        row_heights = [
            item
            for pair
            in zip(row_heights, spacer_heights)
            for item
            in pair
        ]
        row_heights.pop()
        super().__init__(
            data=data,
            colWidths=col_widths,
            rowHeights=row_heights,
            hAlign="LEFT",
            style=TSTYLES["SummaryList"]
        )
