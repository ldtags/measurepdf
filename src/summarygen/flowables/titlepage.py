import math
from typing import Literal
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Table,
    Flowable,
    KeepTogether,
    Paragraph
)

from src import (
    lookups,
    _SYSTEM,
    START_TIME
)
from src.etrm.models import Measure
from src.summarygen.styles import (
    ParagraphStyle,
    PSTYLES,
    TSTYLES,
    COLORS,
    INNER_WIDTH,
    INNER_HEIGHT
)
from src.summarygen.exceptions import SummaryGenError
from src.summarygen.flowables.general import Spacer


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

    Each measure within the summary should be preceded by a title page.
    """

    def __init__(self, measure: Measure):
        self.measure = measure
        self.data: list[Flowable] = []
        self.row_heights: list[Flowable] = []

        self.add_text(measure.name, PSTYLES['TitlePageTitle'])
        self.add_spacer(0.1 * inch)

        link = measure.link
        self.add_text(f"<link href=\"{link}\">{link}/</link>", PSTYLES['TitleLink'])
        self.add_spacer(0.4 * inch)

        self.data.append(self.sections)
        self.row_heights.append(self.sections.total_height)
        super().__init__(
            [
                Table(
                    [[item] for item in self.data],
                    colWidths=INNER_WIDTH,
                    rowHeights=self.row_heights,
                    style=TSTYLES['TitlePage']
                )
            ]
        )

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

        download_date = START_TIME.strftime(rf'%B %{fmt}d, %Y %{fmt}I:%M%p')
        download_section = TitleSection(
            'DOWNLOADED',
            download_date,
            side='right'
        )        

        return TitleSectionContainer([
            [uc_section, pa_section, version_section],
            [start_section, end_section, download_section]
        ])

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
