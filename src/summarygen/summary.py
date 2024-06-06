import os
import re
import shutil
import math
from reportlab.lib.pagesizes import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Table,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    KeepTogether
)

from src.etrm import ETRM_URL
from src.etrm.models import Measure
from src.summarygen.parser import CharacterizationParser, TMP_DIR
from src.summarygen.styling import (
    PAGESIZE,
    X_MARGIN,
    Y_MARGIN,
    PSTYLES,
    TSTYLES,
    INNER_HEIGHT,
    INNER_WIDTH
)
from src.summarygen.rlobjects import (
    BetterTableStyle,
    BetterParagraphStyle
)
from src.summarygen.flowables import NEWLINE


class Story:
    def __init__(self):
        self.contents: list[Flowable] = []
        self.height: float = 0
        self.page_height: float = 0

    def add(self, flowables: Flowable | list[Flowable]):
        if isinstance(flowables, Flowable):
            flowables = [flowables]
        for flowable in flowables:
            self.contents.append(flowable)
            if isinstance(flowable, Table):
                height = math.fsum(flowable._rowHeights)
            else:
                height = flowable._fixedHeight
            self.height += height
            if isinstance(flowable, KeepTogether):
                if self.page_height + height > INNER_HEIGHT:
                    self.page_height = height
                else:
                    self.page_height += height
            elif self.page_height + height > INNER_HEIGHT:
                margin = INNER_HEIGHT - self.page_height
                self.page_height = height - margin
            else:
                self.page_height += height

    def clear(self):
        self.contents = []
        self.height = 0
        self.page_height = 0


def _params_table_row(measure: Measure,
                      label: str,
                      param_name: str
                     ) -> tuple[str, Paragraph]:
    param = measure.get_shared_parameter(param_name)
    if param == None:
        return ('', '')

    return (label, Paragraph(', '.join(sorted(set(param.active_labels))),
                             PSTYLES['SmallParagraph']))


def _link(display_text: str, link: str) -> Paragraph:
    return Paragraph(f'<link href=\"{link}\">{display_text}</link>',
                     PSTYLES['Link'])


def calc_row_heights(data: list[list[str | Paragraph]],
                     table_style: BetterTableStyle,
                     para_styles: tuple[BetterParagraphStyle, ...],
                     base_height: float,
                     base_widths: tuple[float, ...]
                    ) -> list[float]:
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
            scale = width // (base_widths[i])
            leading = row_styles[i].leading
            cell_height = height + scale * leading
            if cell_height > row_height:
                row_height = cell_height
        row_heights.append(row_height)
    return row_heights


class MeasureSummary:
    def __init__(self,
                 dir_path: str,
                 file_name: str='measure_summary',
                 override: bool=True):
        self.measures: list[Measure] = []
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
        parser = CharacterizationParser(measure,
                                        'technology_summary')
        sections = parser.parse()
        self.story.add(header)
        self.story.add(sections)

    def add_parameters_table(self, measure: Measure):
        table_header = Paragraph('Parameters:', PSTYLES['h2'])
        data = [
            _params_table_row(measure,
                              'Measure Application Type',
                              'MeasAppType'),
            _params_table_row(measure, 'Sector', 'Sector'),
            _params_table_row(measure, 'Building Type', 'BldgType'),
            _params_table_row(measure, 'Building Vintage', 'BldgVint'),
            _params_table_row(measure, 'Building Location', 'BldgLoc'),
            _params_table_row(measure, 'Delivery Type', 'DelivType')
        ]
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
            [Paragraph('Cover Sheet', hstyle),
                _link('Cover Sheet', f'{link}/cover-sheet')],
            [Paragraph('Measure Property Data', hstyle),
                _link('Property Data', f'{link}/property-data')],
            [Paragraph('Subscribe', hstyle),
                _link('Subscriptions', f'{link}/subscriptions')],
            [Paragraph('Permutations', hstyle),
                _link('Permutations', f'{link}/permutation-reports')]]
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
        init_height =  table_header._fixedHeight + row_heights[0]
        if self.story.page_height + init_height > INNER_HEIGHT:
            headed_table = KeepTogether([table_header, table])
            self.story.add(headed_table)
        else:
            self.story.add(table_header)
            self.story.add(table)

    def add_measure(self, measure: Measure):
        self.measures.append(measure)
        self.add_measure_details_table(measure)
        self.story.add(NEWLINE)
        self.add_tech_summary(measure)
        self.story.add(NEWLINE)
        self.add_parameters_table(measure)
        self.story.add(NEWLINE)
        self.add_sections_table(measure)
        self.story.add(PageBreak())

    def reset(self):
        self.story.clear()

    def build(self):
        # if multiple measures, maybe add a table of contents
        self.summary.build(self.story.contents)
        if os.path.exists(TMP_DIR):
            shutil.rmtree(TMP_DIR)
