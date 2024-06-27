import os
import re
import shutil
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Table,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    KeepTogether,
    PageTemplate
)
from reportlab.platypus.frames import Frame

from src import lookups
from src.etrm import ETRM_URL, ETRMConnection
from src.etrm.models import Measure
from src.exceptions import SummaryGenError
from src.summarygen.parser import CharacterizationParser, TMP_DIR
from src.summarygen.styling import (
    BetterTableStyle,
    BetterParagraphStyle,
    PAGESIZE,
    X_MARGIN,
    Y_MARGIN,
    PSTYLES,
    TSTYLES,
    INNER_HEIGHT,
    INNER_WIDTH
)
from src.summarygen.flowables import NEWLINE
from src.summarygen.rlobjects import Story
from src.exceptions import (
    ETRMResponseError,
    ETRMRequestError
)


def clean():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)


class FooterCanvas(Canvas):
    """Custom canvas for adding header/footer content"""

    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_canvas()
            Canvas.showPage(self)
        Canvas.save(self)

    def draw_canvas(self, draw_page_num: bool=False):
        self.saveState()
        style = PSTYLES['SmallParagraphBold']
        id_footer = current_measure.full_version_id
        measure_id = Paragraph(id_footer, style=style)
        _, h = measure_id.wrap(INNER_WIDTH, Y_MARGIN)
        x = h * 1.5
        y = h * 1.5
        measure_id.drawOn(canvas=self, x=x, y=y)
        id_width = stringWidth(id_footer, style.font_name, style.font_size)
        name_footer = current_measure.name
        measure_name = Paragraph(name_footer, style=PSTYLES['SmallParagraph'])
        _, h = measure_name.wrap(INNER_WIDTH - id_width, Y_MARGIN)
        measure_name.drawOn(canvas=self, x=x + id_width + 3, y=y)

        if draw_page_num:
            page_number = Paragraph(f'{self._pageNumber}',
                                    PSTYLES['SmallParagraph'])
            _, h = page_number.wrap(X_MARGIN, Y_MARGIN)
            page_number.drawOn(canvas=self,
                               x=PAGESIZE[0] / 2,
                               y=h * 1.5)
        self.restoreState()


def _link(display_text: str, link: str) -> Paragraph:
    """Generates a clickable flowable that contains an external link"""

    return Paragraph(f'<link href=\"{link}\">{display_text}</link>',
                     PSTYLES['Link'])


def calc_row_heights(data: list[list[str | Paragraph]],
                     table_style: BetterTableStyle,
                     para_styles: tuple[BetterParagraphStyle, ...],
                     base_height: float,
                     base_widths: tuple[float, ...]
                    ) -> list[float]:
    """Calculates row heights for static tables"""

    vpadding = table_style.top_padding + table_style.bottom_padding
    hpadding = table_style.left_padding + table_style.right_padding
    height = base_height + vpadding
    row_heights: list[float] = []
    row_styles: tuple[BetterParagraphStyle, ...] = []
    for row in data:
        row_height = height
        if isinstance(para_styles, BetterParagraphStyle):
            row_styles = [para_styles] * len(row)
        elif len(para_styles) == 1:
            row_styles = para_styles * len(row)
        elif len(para_styles) != len(row):
            raise RuntimeError(f'Invalid number of paragraph styles')
        else:
            row_styles = para_styles

        for i, cell in enumerate(row):
            if isinstance(cell, str):
                text = cell
            else:
                text = cell.text
            re_match = re.search(r'<link .+>(.+)</link>', text)
            if re_match != None:
                text = str(re_match.group(1))
            width = stringWidth(text,
                                row_styles[i].font_name,
                                row_styles[i].font_size)
            width += hpadding
            scale = width // (base_widths[i])
            leading = row_styles[i].leading
            cell_height = height + scale * leading
            if cell_height > row_height:
                row_height = cell_height
        row_heights.append(row_height)
    return row_heights


class MeasureSummary:
    """eTRM measure summary PDF generator"""

    def __init__(self,
                 dir_path: str,
                 connection: ETRMConnection,
                 file_name: str='measure_summary',
                 override: bool=True):
        clean()
        self.measures: list[Measure] = []
        self.connection = connection
        self.story = Story()
        if os.path.exists(dir_path):
            self.dir_path = dir_path
        else:
            raise FileNotFoundError(f'no {dir_path} folder exists')
        self.file_name = file_name + '.pdf'
        self.file_path = os.path.join(self.dir_path, self.file_name)
        if not override and os.path.exists(self.file_path):
            raise FileExistsError(f'a file named {file_name} already exists'
                                  f' in {dir_path}')
        self.page_width = PAGESIZE[0]
        self.page_height = PAGESIZE[1]
        self.summary = SimpleDocTemplate(self.file_path,
                                         pagesize=PAGESIZE,
                                         leftMargin=X_MARGIN,
                                         rightMargin=X_MARGIN,
                                         topMargin=Y_MARGIN,
                                         bottomMargin=Y_MARGIN)

    def add_measure_details_table(self, measure: Measure):
        pstyle = PSTYLES['SmallParagraph']
        data: list[tuple[str, Paragraph]] = [
            ['Statewide Measure Id', Paragraph(measure.full_version_id,
                                               pstyle)],
            ['Measure Name', Paragraph(measure.name,
                                       pstyle)],
            ['Effective Date', Paragraph(measure.effective_start_date,
                                         pstyle)],
            ['End Date', Paragraph(measure.sunset_date or '',
                                   pstyle)],
            ['PA Lead', Paragraph(measure.pa_lead, pstyle)]
        ]
        style = TSTYLES['DetailsTable']
        col_widths = (2.25*inch, 3.03*inch)
        base_height = 0.24*inch + style.top_padding + style.bottom_padding
        row_heights = calc_row_heights(data,
                                       style,
                                       pstyle,
                                       base_height,
                                       col_widths)
        table = Table(data,
                      colWidths=col_widths,
                      rowHeights=row_heights,
                      style=style,
                      hAlign='LEFT')
        self.story.add(table)

    def add_tech_summary(self, measure: Measure):
        header = Paragraph('Technology Summary', PSTYLES['h2'])
        parser = CharacterizationParser(measure=measure,
                                        connection=self.connection,
                                        name='technology_summary')
        sections = parser.parse()
        self.story.add(header)
        self.story.add(sections)

    def __add_param_row(self,
                        measure: Measure,
                        label: str,
                        param_name: str,
                        data: list[tuple[str, Paragraph]]):
            param = measure.get_shared_parameter(param_name)
            if param == None:
                param_labels = ''
            else:
                param_labels = ', '.join(sorted(set(param.active_labels)))
            data.append((label, Paragraph(param_labels,
                                          PSTYLES['SmallParagraph'])))

    def add_parameters_table(self, measure: Measure):
        table_header = Paragraph('Parameters:', PSTYLES['h2'])
        data = []
        self.__add_param_row(measure,
                             'Measure Application Type',
                             'MeasAppType',
                             data)
        self.__add_param_row(measure, 'Sector', 'Sector', data)
        self.__add_param_row(measure, 'Building Type', 'BldgType', data)
        self.__add_param_row(measure, 'Building Vintage', 'BldgVint', data)
        self.__add_param_row(measure, 'Building Location', 'BldgLoc', data)
        self.__add_param_row(measure, 'Delivery Type', 'DelivType', data)
        self.__add_param_row(measure, 'Normalized Unit', 'NormUnit', data)
        self.__add_param_row(measure,
                             'Electric Impact Profile ID',
                             'electricImpactProfileID',
                             data)
        self.__add_param_row(measure,
                             'Gas Impact Profile ID',
                             'GasImpactProfileID',
                             data)
        style = TSTYLES['ParametersTable']
        col_widths = (2.26*inch, 3.98*inch)
        base_height = 0.24*inch + style.top_padding + style.bottom_padding
        row_heights = calc_row_heights(data,
                                       style,
                                       PSTYLES['SmallParagraph'],
                                       base_height,
                                       col_widths)
        table = Table(data,
                      colWidths=col_widths,
                      rowHeights=row_heights,
                      style=TSTYLES['ParametersTable'],
                      hAlign='LEFT')
        headed_table = KeepTogether([table_header, table])
        self.story.add(headed_table)

    def add_sections_table(self, measure: Measure):
        table_header = Paragraph('Sections:', PSTYLES['h2'])
        hstyle = PSTYLES['TableHeader']
        id_path = '/'.join(measure.full_version_id.split('-', 1))
        link = f'{ETRM_URL}/measure/{id_path}'
        try:
            ref_id = lookups.PERMUTATION_REFS[measure.use_category]
        except KeyError:
            raise SummaryGenError('unknown use category:'
                                  f' {measure.use_category}')
        try:
            reference = self.connection.get_reference(ref_id)
            perm_link = reference.source_document
        except (ETRMResponseError, ETRMRequestError):
            perm_link = f'{link}/permutation-report'
        data = [
            [Paragraph('Descriptions', hstyle),
                _link('Technology Summary', f'{link}#technology-summary')],
            ['', 
                _link('Measure Case Description',
                      f'{link}#measure-case-description')],
            ['',
                _link('Base Case Description',
                      f'{link}#base-case-description')],
            [Paragraph('Requirements', hstyle),
                _link('Code Requirements', f'{link}#code-requirements')],
            ['',
                _link('Program Requirements',
                      f'{link}#program-requirements')],
            ['',
                _link('Program Exclusions', f'{link}#program-exclusions')],
            ['',
                _link('Data Collection Requirements',
                      f'{link}#data-collection-requirements')],
            [Paragraph('Savings', hstyle),
                _link('Electric Savings (kWh)',
                      f'{link}#electric-savings-kwh')],
            ['',
                _link('Electric Demand Reduction (kW)',
                      f'{link}#peak-electric-demand-reduction-kw')],
            ['',
                _link('Gas Savings (Therms)', f'{link}#gas-savings-therms')],
            [Paragraph('Cost', hstyle),
                _link('Base Case Material Cost ($/Unit)',
                      f'{link}#base-case-material-cost-unit')],
            ['',
                _link('Measure Case Material Cost ($/Unit)',
                      f'{link}#measure-case-material-cost-unit')],
            ['',
                _link('Base Case Labor Cost ($/Unit)',
                      f'{link}#base-case-labor-cost-unit')],
            ['',
                _link('Measure Case Labor Cost ($/Unit)',
                      f'{link}#measure-case-labor-cost-unit')],
            [Paragraph('Other', hstyle),
                _link('Life Cycle', f'{link}#life-cycle')],
            ['',
                _link('Net-to-gross', f'{link}#net-to-gross')],
            ['',
                _link('Gross Savings Installation Adjustment (GSIA)',
                      f'{link}#gross-savings-installation-adjustment-gsia')],
            ['',
                _link('Non-Energy Impacts', f'{link}#non-energy-impacts')],
            [Paragraph('Version Comparison', hstyle),
                _link('Cover Sheet', f'{link}/cover-sheet')],
            [Paragraph('Field Validation List', hstyle),
                _link('Property Data', f'{link}/property-data')],
            [Paragraph('Subscribe', hstyle),
                _link('Subscriptions', f'{link}/subscriptions')],
            [Paragraph('Permutations', hstyle),
                _link('Permutations', perm_link)]]
        tstyle = TSTYLES['SectionsTable']
        para_styles = (PSTYLES['TableHeader'], PSTYLES['Link'])
        col_widths = (1.42*inch, 4.81*inch)
        base_height = PSTYLES['TableHeader'].leading
        row_heights = calc_row_heights(data,
                                       tstyle,
                                       para_styles,
                                       base_height,
                                       col_widths)
        table = Table(data,
                      colWidths=col_widths,
                      rowHeights=row_heights,
                      style=tstyle,
                      hAlign='LEFT')
        headed_table = KeepTogether([table_header, table])
        self.story.add(headed_table)

    def add_measure(self, measure: Measure):
        global current_measure
        current_measure = measure
        self.measures.append(measure)
        frame = Frame(x1=X_MARGIN,
                      y1=Y_MARGIN,
                      width=INNER_WIDTH,
                      height=INNER_HEIGHT,
                      id='normal')
        template = PageTemplate(id=measure.full_version_id, frames=frame)
        self.summary.addPageTemplates([template])

        self.add_measure_details_table(measure)
        self.story.add(NEWLINE)
        self.add_tech_summary(measure)
        self.story.add(NEWLINE)
        self.add_parameters_table(measure)
        self.add_sections_table(measure)
        self.story.add(PageBreak())

    def reset(self):
        self.story.clear()

    def build(self):
        # if multiple measures, maybe add a table of contents
        self.summary.multiBuild(self.story.contents, canvasmaker=FooterCanvas)
        clean()
