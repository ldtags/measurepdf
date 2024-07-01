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
    BaseDocTemplate,
    KeepTogether,
    PageTemplate,
    NextPageTemplate
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
    ETRMConnectionError,
    ETRMResponseError,
    ETRMRequestError
)


def clean():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)


class SummaryDocTemplate(BaseDocTemplate):
    def __init__(self,
                 filename: str,
                 pagesize: tuple[float, float]=PAGESIZE,
                 left_margin: float=X_MARGIN,
                 right_margin: float=X_MARGIN,
                 top_margin: float=Y_MARGIN,
                 bottom_margin: float=Y_MARGIN,
                 *args,
                 **kwargs):
        BaseDocTemplate.__init__(self,
                                 filename=filename,
                                 pagesize=pagesize,
                                 leftMargin=left_margin,
                                 rightMargin=right_margin,
                                 topMargin=top_margin,
                                 bottomMargin=bottom_margin,
                                 *args,
                                 **kwargs)

        self.left_margin = left_margin
        self.right_margin = right_margin
        self.top_margin = top_margin
        self.bottom_margin = bottom_margin
        self.page_width = pagesize[0]
        x_margin = self.left_margin + self.right_margin
        self.inner_width = self.page_width - x_margin
        self.page_height = pagesize[1]
        y_margin = self.top_margin + self.bottom_margin
        self.inner_height = self.page_height - y_margin
        self.__page_num = 1

    def afterPage(self):
        """Called after all flowables have been drawn on a page"""

        self.__page_num += 1


class SummaryPageTemplate(PageTemplate):
    def __init__(self,
                 measure_id: str,
                 measure_name: str,
                 frames: Frame | list[Frame]):
        self.measure_id = measure_id
        self.measure_name = measure_name
        PageTemplate.__init__(self, id=measure_id, frames=frames)

    def draw_footer(self,
                    canv: Canvas,
                    doc: SummaryDocTemplate,
                    draw_page_num: bool=False
                   ) -> None:
            """Used to draw a custom footer depending on the current state
            of the doc template.
            """

            canv.saveState()

            style = PSTYLES['SmallParagraphBold']
            id_footer = Paragraph(self.measure_id, style=style)
            _, h = id_footer.wrap(INNER_WIDTH, Y_MARGIN)
            x = h * 1.5
            y = h * 1.5
            id_footer.drawOn(canvas=canv, x=x, y=y)
            id_width = stringWidth(self.measure_id,
                                   style.font_name, 
                                   style.font_size)
            name_footer = Paragraph(self.measure_name,
                                    style=PSTYLES['SmallParagraph'])
            _, h = name_footer.wrap(INNER_WIDTH - id_width, Y_MARGIN)
            name_footer.drawOn(canvas=canv, x=x + id_width + 3, y=y)

            if draw_page_num:
                page_number = Paragraph(f'{doc.__page_num}',
                                        PSTYLES['SmallParagraph'])
                _, h = page_number.wrap(X_MARGIN, Y_MARGIN)
                page_number.drawOn(canvas=canv,
                                   x=PAGESIZE[0] / 2,
                                   y=h * 1.5)

            canv.restoreState()

    def afterDrawPage(self, canv: Canvas, doc: SummaryDocTemplate):
        self.draw_footer(canv, doc)


def calc_col_widths(data: list[list[str | Paragraph]],
                    table_style: BetterTableStyle,
                    para_styles: tuple[BetterParagraphStyle, ...]
                   ) -> list[float]:
    


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
        self.summary = SummaryDocTemplate(self.file_path)

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

    def __build_parameters_table(self,
                                 params: list[tuple[str, str]],
                                 measure: Measure
                                ) -> Table:
        data: list[tuple[str, str]] = []
        for label, api_name in params:
            param = measure.get_shared_parameter(api_name)
            if param == None:
                param_labels = ''
            else:
                param_labels = ', '.join(sorted(set(param.active_labels)))
            data.append((label, param_labels))

        style = PSTYLES['SmallParagraph']
        formatted_data: list[tuple[Paragraph, Paragraph]] = []
        for label, item in data:
            label_para = Paragraph(label, style=PSTYLES['Paragraph'])
            item_para = Paragraph(item, PSTYLES['SmallParagraph'])
            formatted_data.append((label_para, item_para))

        style = TSTYLES['ParametersTable']
        para_styles = (PSTYLES['Paragraph'], PSTYLES['SmallParagraph'])
        col_widths = (2.26*inch, 3.98*inch)
        base_height = 0.24*inch + style.top_padding + style.bottom_padding
        row_heights = calc_row_heights(formatted_data,
                                       style,
                                       para_styles,
                                       base_height,
                                       col_widths)
        return Table(formatted_data,
                     colWidths=col_widths,
                     rowHeights=row_heights,
                     style=TSTYLES['ParametersTable'],
                     hAlign='LEFT')


    def add_parameters_table(self, measure: Measure):
        params = [
            ('Measure Application Type', 'MeasAppType'),
            ('Sector', 'Sector'),
            ('Building Type', 'BldgType'),
            ('Building Vintage', 'BldgVint'),
            ('Building Location', 'BldgLoc'),
            ('Delivery Type', 'DelivType'),
            ('Normalized Unit', 'NormUnit'),
            ('Electric Impact Profile ID', 'electricImpactProfileID'),
            ('Gas Impact Profile ID', 'GasImpactProfileID'),
            ('Effective Useful Life ID', 'EULID')
        ]
        impacts = [
            ('Effective Useful Life (Years)', 'EULID', 'EUL_Yrs'),
            ('Remaining Useful Life (Years)', 'EULID', 'RUL_Yrs')
        ]
        table = self.__build_parameters_table(params, impacts, measure)
        table_header = Paragraph('Parameters:', PSTYLES['h2'])
        self.story.add(KeepTogether([table_header, table]))

    def __get_impact(self,
                     param_name: str,
                     column: str,
                     measure: Measure) -> str:
        shared_param = measure.get_shared_parameter(param_name)
        if shared_param is None:
            return ''

        try:
            table_name = lookups.SHARED_VALUE_TABLES[shared_param.name]
        except KeyError:
            return ''
        shared_lookup = measure.get_shared_lookup(table_name)
        if shared_lookup is None:
            return ''

        try:
            value_table = self.connection.get_shared_value_table(shared_lookup)
        except ETRMConnectionError:
            return ''

        impacts: list[float] = []
        for label in shared_param.active_labels:
            try:
                impact = value_table[label][column]
                if isinstance(impact, str):
                    try:
                        impact = float(impact)
                    except ValueError:
                        impact = 0
                impacts.append(impact or 0)
            except KeyError:
                continue

        impact_avg = sum(impacts) / len(impacts)
        if impact_avg == 0:
            return ''
        return f'{impact_avg:.2f}'

    def add_impact_table(self, measure: Measure):
        table_header = Paragraph('Impact:', style=PSTYLES['h2'])
        data = [
            ('Effective Useful Life (Years)',
                self.__get_impact('EULID', 'EUL_Yrs', measure)),
            ('Remaining Useful Life (Years)',
                self.__get_impact('EULID', 'RUL_Yrs', measure))
        ]

    def __build_sections_table(self,
                               sections: list[tuple[str, str, str]]
                              ) -> Table:
        data: list[tuple[Paragraph | str, Paragraph]] = []
        for title, label, link in sections:
            if title != '':
                title_para = Paragraph(title, style=PSTYLES['TableHeader'])
            else:
                title_para = ''
            link_para = Paragraph(f'<link href=\"{link}\">{label}</link>',
                                  PSTYLES['Link'])
            data.append((title_para, link_para))
        tstyle = TSTYLES['SectionsTable']
        para_styles = (PSTYLES['TableHeader'], PSTYLES['Link'])
        col_widths = (1.42*inch, 4.81*inch)
        base_height = PSTYLES['TableHeader'].leading
        row_heights = calc_row_heights(data,
                                       tstyle,
                                       para_styles,
                                       base_height,
                                       col_widths)
        return Table(data,
                     colWidths=col_widths,
                     rowHeights=row_heights,
                     style=tstyle,
                     hAlign='LEFT')

    def add_sections_table(self, measure: Measure):
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
        sections = [
            ('Descriptions',
                'Technology Summary',
                f'{link}#technology-summary'),
            ('',
                'Measure Case Description',
                f'{link}#measure-case-description'),
            ('',
                'Base Case Description',
                f'{link}#base-case-description'),
            ('Requirements',
                'Code Requirements',
                f'{link}#code-requirements'),
            ('',
                'Program Requirements',
                f'{link}#program-requirements'),
            ('',
                'Program Exclusions',
                f'{link}#program-exclusions'),
            ('',
                'Data Collection Requirements',
                f'{link}#data-collection-requirements'),
            ('Savings',
                'Electric Savings (kWh)',
                f'{link}#electric-savings-kwh'),
            ('',
                'Electric Demand Reduction (kW)',
                f'{link}#peak-electric-demand-reduction-kw'),
            ('',
                'Gas Savings (Therms)',
                f'{link}#gas-savings-therms'),
            ('Cost',
                'Base Case Material Cost ($/Unit)',
                f'{link}#base-case-material-cost-unit'),
            ('',
                'Measure Case Material Cost ($/Unit)',
                f'{link}#measure-case-material-cost-unit'),
            ('',
                'Base Case Labor Cost ($/Unit)',
                f'{link}#base-case-labor-cost-unit'),
            ('',
                'Measure Case Labor Cost ($/Unit)',
                f'{link}#measure-case-labor-cost-unit'),
            ('Other',
                'Life Cycle',
                f'{link}#life-cycle'),
            ('',
                'Net-to-gross',
                f'{link}#net-to-gross'),
            ('',
                'Gross Savings Installation Adjustment (GSIA)',
                f'{link}#gross-savings-installation-adjustment-gsia'),
            ('',
                'Non-Energy Impacts',
                f'{link}#non-energy-impacts'),
            ('Version Comparison',
                'Cover Sheet',
                f'{link}/cover-sheet'),
            ('Field Validation List',
                'Property Data',
                f'{link}/property-data'),
            ('Subscribe',
                'Subscriptions',
                f'{link}/subscriptions'),
            ('Permutations',
                'Permutations',
                perm_link)
        ]
        table = self.__build_sections_table(sections)
        table_header = Paragraph('Sections:', PSTYLES['h2'])
        self.story.add(KeepTogether([table_header, table]))

    def add_measure(self, measure: Measure):
        self.measures.append(measure)
        frame = Frame(x1=self.summary.left_margin,
                      y1=self.summary.bottom_margin,
                      width=INNER_WIDTH,
                      height=INNER_HEIGHT,
                      id='normal')
        template = SummaryPageTemplate(measure_id=measure.full_version_id,
                                       measure_name=measure.name,
                                       frames=frame)
        self.summary.addPageTemplates(template)

    def reset(self):
        self.story.clear()

    def __build_summary(self, measure: Measure):
        self.story.add(NextPageTemplate(measure.full_version_id))
        if self.measures.index(measure) != 0:
            self.story.add(PageBreak())
        self.add_measure_details_table(measure)
        self.story.add(NEWLINE)
        self.add_tech_summary(measure)
        self.story.add(NEWLINE)
        self.add_parameters_table(measure)
        self.add_sections_table(measure)

    def build(self):
        for measure in self.measures:
            self.__build_summary(measure)
        self.summary.multiBuild(self.story.contents)
        clean()
