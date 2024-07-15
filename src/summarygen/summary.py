import os
import re
import math
import shutil
import logging
from typing import overload
from reportlab.lib.units import inch
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
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.frames import Frame

from src import lookups, patterns, utils, _SYSTEM, _NOW
from src.etrm.models import ETRM_URL, Measure
from src.etrm.connection import ETRMConnection
from src.etrm.exceptions import (
    ETRMConnectionError,
    ETRMResponseError,
    ETRMRequestError
)
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
from src.summarygen.rlobjects import Story
from src.summarygen.flowables import (
    NEWLINE,
    SummaryTable,
    Spacer,
    TitleSection,
    TitleSectionContainer
)
from src.summarygen.exceptions import SummaryGenError


logger = logging.getLogger(__name__)


def clean():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)


class NumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """add page info to each page (page x of y)"""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            Canvas.showPage(self)
        Canvas.save(self)

    def draw_page_number(self, page_count: int):
        style = PSTYLES['SmallParagraph']
        text = f'{self.getPageNumber()}/{page_count}'
        page_number = Paragraph(text, style=style)
        _, h = page_number.wrap(X_MARGIN, Y_MARGIN)
        num_width = stringWidth(text,
                                style.font_name,
                                style.font_size)
        page_number.drawOn(canvas=self,
                           x=PAGESIZE[0] - X_MARGIN / 1.5 - num_width,
                           y=h * 1.5)


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
        self.pt_index = -1

    def afterPage(self) -> None:
        try:
            next_pt_index = self._nextPageTemplateIndex
            if next_pt_index != self.pt_index:
                if self.pt_index == -1:
                    prev_template = None
                else:
                    prev_template = self.pageTemplates[self.pt_index]
                    assert isinstance(prev_template, SummaryPageTemplate)
                cur_template = self.pageTemplates[next_pt_index]
                assert isinstance(cur_template, SummaryPageTemplate)
                if self.page != 2:
                    page = self.page + 1
                else:
                    page = self.page
                prev_category = ''
                if prev_template is not None:
                    prev_id = prev_template.id
                    if prev_id is not None:
                        re_match = re.search(patterns.VERSION_ID, prev_id)
                        if re_match is not None:
                            prev_category = str(re_match.group(4))
                cur_id = cur_template.id
                if cur_id is not None:
                    re_match = re.search(patterns.VERSION_ID, cur_id)
                    if re_match is not None:
                        cur_category = str(re_match.group(4))
                        if prev_category != cur_category:
                            uc_name = lookups.USE_CATEGORIES[cur_category]
                            text = f'{cur_category} - {uc_name}'
                            self.notify('TOCEntry', (0, text, page))
                key = self.canv.bookmarkPage(cur_template.id)
                text = f'{cur_template.id} - {cur_template.measure_name}'
                self.notify('TOCEntry', (1, text, page))
                self.pt_index = next_pt_index
        except AttributeError:
            pass


class SummaryPageTemplate(PageTemplate):
    def __init__(self,
                 measure_id: str,
                 measure_name: str):
        self.measure_id = measure_id
        self.measure_name = measure_name
        frame = Frame(x1=X_MARGIN,
                      y1=Y_MARGIN,
                      width=INNER_WIDTH,
                      height=INNER_HEIGHT,
                      leftPadding=0,
                      rightPadding=0,
                      topPadding=0,
                      bottomPadding=0,
                      id='normal')
        PageTemplate.__init__(self, id=measure_id, frames=frame)

    def draw_footer(self,
                    canv: Canvas,
                    doc: SummaryDocTemplate
                   ) -> None:
            canv.saveState()

            style = PSTYLES['SmallParagraph'].bold
            id_footer = Paragraph(self.measure_id, style=style)
            _, h = id_footer.wrap(INNER_WIDTH, Y_MARGIN)
            x = X_MARGIN / 1.5
            y = h * 1.5
            id_footer.drawOn(canvas=canv, x=x, y=y)
            id_width = stringWidth(self.measure_id,
                                   style.font_name, 
                                   style.font_size)
            name_footer = Paragraph(self.measure_name,
                                    style=PSTYLES['SmallParagraph'])
            _, h = name_footer.wrap(INNER_WIDTH - id_width, Y_MARGIN)
            name_footer.drawOn(canvas=canv, x=x + id_width + 3, y=y)

            canv.restoreState()

    def draw_header(self,
                    canv: Canvas,
                    doc: SummaryDocTemplate
                   ) -> None:
        canv.saveState()

        if _SYSTEM == 'Windows':
            fmt = '#'
        else:
            fmt = '-'
        cur_dt = _NOW.strftime(rf'%{fmt}m/%{fmt}d/%y, %{fmt}I:%M%p')
        style = PSTYLES['SmallBase']
        time_header = Paragraph(cur_dt, style=style)
        _, h = time_header.wrap(INNER_WIDTH + X_MARGIN, Y_MARGIN)
        y = PAGESIZE[1] - Y_MARGIN / 2 + h / 2
        time_header.drawOn(canv, x=X_MARGIN / 1.5, y=y)

        canv.restoreState()

    def afterDrawPage(self, canv: Canvas, doc: SummaryDocTemplate) -> None:
        self.draw_footer(canv, doc)
        self.draw_header(canv, doc)


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
        self.measures: dict[str, list[Measure]] = {}
        self.__cur_measure: Measure | None = None
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

    def contains(self, measure: Measure) -> bool:
        try:
            existing_measures = self.measures[measure.use_category]
            for existing_measure in existing_measures:
                if measure.full_version_id == existing_measure.full_version_id:
                    return False
        except KeyError:
            pass
        return False

    def is_last(self, measure: Measure) -> bool:
        if len(self.measures) == 0:
            return False

        if not self.contains(measure):
            return False

        last_uc = sorted(self.measures.keys())[-1]
        if measure.use_category != last_uc:
            return False

        measures = self.measures[last_uc]
        if measures[-1].full_version_id != measure.full_version_id:
            return False

        return True

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
        download_date = _NOW.strftime(rf'%B %{fmt}d, %Y %{fmt}I:%M%p')
        download_section = TitleSection('DOWNLOADED',
                                          download_date,
                                          side='right')        

        sections = [
            [uc_section, pa_section, version_section],
            [start_section, end_section, download_section]
        ]
        return TitleSectionContainer(sections)

    def add_title_page(self):
        if self.__cur_measure is None:
            return

        img_path = utils.asset_path('etrm.png', 'images')
        img = utils.get_rlimage(img_path, INNER_WIDTH / 9, hAlign='LEFT')
        self.story.add(img)
        self.story.add(Spacer(1, 1.5 * inch))

        self.story.add(Paragraph('MEASURE CHARACTERIZATION',
                                 style=PSTYLES['TitlePageSubtitle']))
        self.story.add(Spacer(1, 0.15 * inch))

        self.story.add(Paragraph(self.__cur_measure.name,
                                 style=PSTYLES['TitlePageTitle']))
        self.story.add(NEWLINE)

        link = self.__cur_measure.link
        link_xml = f'<link href=\"{link}\">{link}/</link>'
        self.story.add(Paragraph(link_xml, style=PSTYLES['TitleLink']))
        self.story.add(Spacer(1, 1 * inch))

        container = self.__build_sections_container(self.__cur_measure)
        self.story.add(container)

        self.story.add(PageBreak())

    def add_tech_summary(self):
        header = Paragraph('Technology Summary', PSTYLES['h2'])
        parser = CharacterizationParser(measure=self.__cur_measure,
                                        connection=self.connection,
                                        name='technology_summary')
        flowables = parser.parse()
        self.story.add(header, NEWLINE, *flowables, NEWLINE)

    def add_use_category_page(self, use_category: str) -> None:
        ...

    def __get_shared_avg(self,
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
                col_data = value_table.data[label][column]
                vals = list(
                    filter(
                        lambda val: val is not None,
                        col_data
                    )
                )
                avg = math.fsum(vals) / len(vals)
                impacts.append(avg)
            except KeyError:
                continue

        if len(impacts) == 0:
            return ''

        impact_avg = sum(impacts) / len(impacts)
        if impact_avg == 0:
            return ''
        return f'{impact_avg:.2f}'

    def __build_parameters_table(self,
                                 params: list[tuple[str, str]],
                                 impacts: list[tuple[str, str]]=[]
                                ) -> Table:
        data: list[tuple[str, str]] = []
        for label, api_name in params:
            param = self.__cur_measure.get_shared_parameter(api_name)
            if param == None:
                param_labels = ''
            else:
                param_labels = ', '.join(sorted(set(param.active_labels)))
            data.append((label, param_labels))

        for label, api_name, column_name in impacts:
            impact = self.__get_shared_avg(param_name=api_name,
                                           column=column_name,
                                           measure=self.__cur_measure)
            data.append((label, impact))
        
        return SummaryTable(data,
                            header_orient='left',
                            header_style=PSTYLES['Paragraph'],
                            body_style=PSTYLES['SmallBase'])

    def add_parameters_table(self):
        if self.__cur_measure is None:
            return

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
        table = self.__build_parameters_table(params, impacts)
        table_header = Paragraph('Parameters:', PSTYLES['h2'])
        self.story.add(KeepTogether([table_header, table]), NEWLINE)

    def add_impact_table(self):
        if self.__cur_measure is None:
            return

        permutations = self.connection.get_permutations(self.__cur_measure)
        first_baseline = permutations.get_first_baseline()
        second_baseline = permutations.get_second_baseline()
        first_mtc = permutations.average('UnitMeaCost1stBaseline')
        second_mtc = permutations.average('UnitMeaCost2ndBaseline')
        mat_param = self.__cur_measure.get_shared_parameter('MeasAppType')
        if mat_param != None:
            if all(x in mat_param.active_labels for x in [['NC', 'NR']]):
                standard = first_baseline
                pre_existing = 0.0
                inc_cost = first_mtc
                full_cost = 0.0
            elif 'AR' in mat_param.active_labels:
                standard = second_baseline
                pre_existing = first_baseline
                inc_cost = second_mtc
                full_cost = first_mtc
            else:
                standard = 0.0
                pre_existing = first_baseline
                inc_cost = 0.0
                full_cost = first_mtc

        data: list[tuple[str, str]] = [
            ('Standard', f'{standard:.2f}'),
            ('Pre-Existing', f'{pre_existing:.2f}'),
            ('Incremental Cost', f'{inc_cost:.2f}'),
            ('Full Measure Cost', f'{full_cost:.2f}')
        ]
        table = SummaryTable(data,
                             header_orient='left',
                             header_style=PSTYLES['Paragraph'],
                             body_style=PSTYLES['SmallParagraph'])
        header = Paragraph('Impact:', style=PSTYLES['h2'])
        self.story.add(KeepTogether([header, table]), NEWLINE)

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

    def add_sections_table(self):
        if self.__cur_measure is None:
            return

        measure = self.__cur_measure
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

    def add_table_of_contents(self):
        toc_header = Paragraph('Table of Contents', style=PSTYLES['TOCHeader'])
        self.story.add(toc_header, NEWLINE)
        self.story.add(TableOfContents())
        self.story.add(PageBreak())

    @overload
    def add_measure(self, measure_id: str) -> None:
        ...

    @overload
    def add_measure(self, measure: Measure) -> None:
        ...

    def add_measure(self, *args, **kwargs) -> None:
        try:
            arg = args[0]
        except IndexError:
            arg = kwargs.get('measure_id')
            if arg is None:
                arg = kwargs.get('measure')

        if isinstance(arg, str):
            measure = self.connection.get_measure(arg)
        elif isinstance(arg, Measure):
            measure = arg
        else:
            raise RuntimeError(f'Unsupported arg type: {type(arg)}')

        if self.contains(measure):
            return

        try:
            self.measures[measure.use_category].append(measure)
            self.measures[measure.use_category].sort(key=Measure.sorting_key)
        except KeyError:
            self.measures[measure.use_category] = [measure]
        template = SummaryPageTemplate(measure_id=measure.full_version_id,
                                       measure_name=measure.name)
        self.summary.addPageTemplates(template)

    def add_use_category(self, use_category: str) -> None:
        logger.info(f'Adding use category {use_category}')

        measure_ids = self.connection.get_all_measure_ids(use_category)
        versions: list[str] = []
        for measure_id in measure_ids:
            measure_versions = self.connection.get_measure_versions(measure_id)
            measure_versions.sort(key=utils.version_key)
            recent_version: str | None = None
            for measure_version in measure_versions:
                if measure_version.count('-') == 1:
                    recent_version = measure_version
                    break
            if recent_version is not None:
                versions.append(recent_version)

        for version_id in versions:
            self.add_measure(version_id)

    def reset(self):
        self.story.clear()

    def __build_summary(self, measure: Measure | None=None):
        if measure is None:
            if self.__cur_measure is None:
                raise RuntimeError('Missing Measure: no measure provided'
                                        ' to build a summary with')
            summary_measure = self.__cur_measure
        else:
            summary_measure = measure
            self.__cur_measure = measure

        logger.info('Building summary for measure'
                        f' {summary_measure.full_version_id}')

        self.story.add(NextPageTemplate(summary_measure.full_version_id))
        self.add_title_page()
        self.add_tech_summary()
        self.add_parameters_table()
        self.add_impact_table()
        self.add_sections_table()

        self.__cur_measure = None

    def build(self):
        if len(self.measures) > 1:
            self.add_table_of_contents()

        for use_category in sorted(self.measures.keys()):
            self.add_use_category_page(use_category)
            for measure in self.measures[use_category]:
                self.__build_summary(measure)
                if not self.is_last(measure):
                    self.story.add(PageBreak())
        self.summary.multiBuild(self.story.contents,
                                canvasmaker=NumberedCanvas)
        clean()
