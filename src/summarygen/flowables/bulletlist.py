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
from src.summarygen.exceptions import SummaryGenError


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
