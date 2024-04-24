import os
from reportlab.lib.pagesizes import inch, letter, mm
from reportlab.platypus import (
    Flowable,
    Table,
    Paragraph,
    PageBreak,
    SimpleDocTemplate,
    Spacer
)

from src import _ROOT
from src.etrm.models import Measure
from src.summarygen.parser import parse_characterization
from src.summarygen.styling import STYLES


NEWLINE = Spacer(letter[0], 17.5)


def _params_table_row(measure: Measure,
                      label: str,
                      param_name: str
                     ) -> tuple[str, str]:
    param = measure.get_shared_parameter(param_name)
    if param == None:
        return ('', '')

    return (label, ', '.join(sorted(set(param.active_labels))))


def _link(display_text: str, link: str) -> Paragraph:
    return Paragraph(f'<link href=\"{link}\">{display_text}</link>',
                     STYLES['Link'])


def _theader(text: str) -> Paragraph:
    return Paragraph(text, STYLES['TableHeader'])


def get_row_heights(data: list[list],
                    base_height: float,
                    col_widths: tuple[float, ...] | float
                   ) -> tuple[float, ...]:
    pass


class MeasureSummary:
    def __init__(self,
                 file_name: str='measure_summary',
                 relative_dir: str='',
                 override: bool=False):
        self.measures: list[Measure] = []
        self.flowables: list[Flowable] = []
        if not os.path.exists(os.path.join(_ROOT, '..', relative_dir)):
            raise FileNotFoundError(f'no {relative_dir} folder exists')
        self.relative_dir = relative_dir
        self.file_name = file_name + '.pdf'
        self.file_path = os.path.join(self.relative_dir, self.file_name)
        if not override and os.path.exists(self.file_path):
            raise FileExistsError(f'a file named {file_name} already exists'
                                  f' in {relative_dir}')
        self.summary = SimpleDocTemplate(self.file_path, pagesize=letter)

    def add_measure_details_table(self, measure: Measure):
        data = [
            ['Statewide Measure Id', measure.full_version_id],
            ['Measure Name', measure.name],
            ['Effective Date', measure.effective_start_date],
            ['End Date', measure.sunset_date or ''],
            ['PA Lead', measure.pa_lead]
        ]
        table = Table(data,
                      colWidths=(2.25*inch, 3.03*inch),
                      rowHeights=(0.24*inch),
                      style=STYLES['DetailsTable'],
                      hAlign='LEFT')
        self.flowables.append(table)

    def add_tech_summary(self, html: str):
        self.flowables.append(Paragraph('Technology Summary',
                                        STYLES['Header']))
        self.flowables.extend(parse_characterization(html))

    def add_parameters_table(self, measure: Measure):
        self.flowables.append(Paragraph('Parameters:', STYLES['Header']))
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
        table = Table(data,
                      colWidths=(2.26*inch, 3.98*inch),
                      rowHeights=(0.24*inch),
                      style=STYLES['ParametersTable'],
                      hAlign='LEFT')
        self.flowables.append(table)

    def add_sections_table(self, measure: Measure):
        self.flowables.append(Paragraph('Sections:',
                                        STYLES['Header']))
        id_path = '/'.join(measure.full_version_id.split('-'))
        link = f'https://www.caetrm.com/measure/{id_path}'
        data = [
            [_theader('Descriptions'),
                _link('Technology Summary', f'{link}#technology-summary')],
            ['', 
                _link('Measure Case Description',
                      f'{link}#measure-case-description')],
            ['',
                _link('Base Case Description',
                      f'{link}#base-case-description')],
            [_theader('Requirements'),
                _link('Code Requirements', f'{link}#code-requirements')],
            ['',
                _link('Program Requirements',
                      f'{link}#program-requirements')],
            ['',
                _link('Program Exclusions', f'{link}#program-exclusions')],
            ['',
                _link('Data Collection Requirements',
                      f'{link}#data-collection-requirements')],
            [_theader('Savings'),
                _link('Electric Savings (kWh)',
                      f'{link}#electric-savings-kwh')],
            ['',
                _link('Electric Demand Reduction (kW)',
                      f'{link}#peak-electric-demand-reduction-kw')],
            ['',
                _link('Gas Savings (Therms)', f'{link}#gas-savings-therms')],
            [_theader('Cost'),
                _link('Base Case Material Cost ($/Unit)',
                      f'{link}#base-case-material-cost-unit')],
            ['',
                _link('Measure Case Material Cost ($/Unit)',
                      f'{link}#measure-case-material-cost')],
            ['',
                _link('Base Case Labor Cost ($/Unit)',
                      f'{link}#base-case-labor-cost-unit')],
            ['',
                _link('Measure Case Labor Cost ($/Unit)',
                      f'{link}#measure-case-labor-cost-unit')],
            [_theader('Other'),
                _link('Life Cycle', f'{link}#life-cycle')],
            ['',
                _link('Net-to-gross', f'{link}#net-to-gross')],
            ['',
                _link('Gross Savings Installation Adjustment (GSIA)',
                      f'{link}#gross-savings-installation-adjustment-gsia')],
            ['',
                _link('Non-Energy Impacts', f'{link}#non-energy-impacts')],
            [_theader('Cover Sheet'),
                _link('Cover Sheet', f'{link}#cover-sheet')],
            [_theader('Measure Property Data'),
                _link('Property Data', f'{link}#property-data')],
            [_theader('Subscribe'),
                _link('Subscriptions', f'{link}/subscriptions')],
            [_theader('Permutations'),
                _link('Permutations', f'{link}/permutations')]]
        row_heights = (*(19*[0.24*inch]), 0.48*inch, *(2*[0.24*inch]))
        table = Table(data,
                      colWidths=(1.42*inch, 4.81*inch),
                      rowHeights=row_heights,
                      style=STYLES['SectionsTable'],
                      hAlign='LEFT')
        self.flowables.append(table)

    def add_measure(self, measure: Measure):
        self.measures.append(measure)
        self.add_measure_details_table(measure)
        self.flowables.append(NEWLINE)
        # self.add_tech_summary(measure.characterizations['technology_summary'])
        # self.flowables.append(NEWLINE)
        self.add_parameters_table(measure)
        self.flowables.append(NEWLINE)
        self.add_sections_table(measure)
        self.flowables.append(NEWLINE)
        self.flowables.append(PageBreak())

    def reset(self):
        self.flowables = []

    def build(self):
        # if multiple measures, maybe add a table of contents
        self.summary.build(self.flowables)
    