import os
import re
import math
import shutil
import logging
import datetime
from typing import overload, TypeVar
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Table,
    Paragraph,
    PageBreak,
    BaseDocTemplate,
    KeepTogether,
    PageTemplate,
    NextPageTemplate,
    Spacer,
    Flowable
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.frames import Frame

from src import (
    lookups,
    patterns,
    resources,
    utils,
    _SYSTEM,
    START_TIME,
    TMP_DIR
)
from src.etrm import ETRM_URL
from src.etrm.models import Measure
from src.etrm.connection import ETRMConnection
from src.etrm.exceptions import (
    ETRMConnectionError,
    ETRMResponseError
)
from src.resources import KeyTerminology
from src.summarygen.utils import get_flowable_height, get_flowable_width
from src.summarygen.models import Story, SQUARE_BULLET
from src.summarygen.styles import (
    TableStyle,
    ParagraphStyle,
    PAGESIZE,
    X_MARGIN,
    Y_MARGIN,
    PSTYLES,
    INNER_HEIGHT,
    INNER_WIDTH,
    TSTYLES,
    NL_HEIGHT,
    DEF_PSTYLE,
    DEFAULT_INDENT_SIZE,
    DEFAULT_PARA_SPACING,
    get_key_terminology_table_style
)
from src.summarygen.parser import HTMLParser
from src.summarygen.generator import FlowableGenerator
from src.summarygen.flowables import (
    NEWLINE,
    BasicTable,
    TitlePage,
    ExcelLink,
    SunsettedMeasuresTable
)
from src.summarygen.exceptions import SummaryGenError


logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def clean():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)


class NumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        try:
            self._startPage()
        except AttributeError:
            raise SummaryGenError('Canvas Build Error: could not show page'
                                  f' {len(self._saved_page_states)}.')

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
    def __init__(
        self,
        filename: str,
        pagesize: tuple[float, float]=PAGESIZE,
        left_margin: float=X_MARGIN,
        right_margin: float=X_MARGIN,
        top_margin: float=Y_MARGIN,
        bottom_margin: float=Y_MARGIN,
        *args,
        **kwargs
    ) -> None:
        BaseDocTemplate.__init__(
            self,
            filename=filename,
            pagesize=pagesize,
            leftMargin=left_margin,
            rightMargin=right_margin,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
            *args,
            **kwargs
        )

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

    def handle_nextPageTemplate(
        self,
        pt: str | int | list[str] | tuple[str, ...]
    ) -> None:
        return super().handle_nextPageTemplate(pt)

    def get_previous_page_template(self) -> PageTemplate | None:
        if self.pageTemplates == []:
            return None

        if self.pt_index == -1:
            return None

        return self.pageTemplates[self.pt_index]

    def get_current_pt_index(self) -> int:
        if self.pageTemplates == []:
            return -1

        try:
            pt_index = self._nextPageTemplateIndex
        except AttributeError:
            return -1

        return pt_index

    def get_current_page_template(self) -> PageTemplate | None:
        pt_index = self.get_current_pt_index()
        if pt_index == -1:
            return None
        return self.pageTemplates[pt_index]

    def add_toc_entry(
        self,
        level: int,
        page: int,
        use_category: str | None=None,
        measure_id: str | None=None
    ) -> None:
        if use_category is not None and measure_id is not None:
            raise RuntimeError('use_category and measure_id are mutually exclusive')

        if use_category is not None:
            try:
                verbose_name = lookups.USE_CATEGORIES[use_category]
            except KeyError:
                raise SummaryGenError(f'Invalid use category: {use_category}')
            text = f'{use_category} - {verbose_name}'
        elif measure_id is not None:
            text = measure_id
        else:
            raise SummaryGenError('One of either use_category or measure_id'
                                  ' are required to create a TOC entry')

        self.notify('TOCEntry', (level, text, page))

    def after_page_toc_handler(self) -> None:
        cur_template = self.get_current_page_template()
        if cur_template is None or cur_template.id is None:
            return

        cur_match = re.fullmatch(patterns.VERSION_ID, cur_template.id)
        if cur_match is None:
            return

        cur_uc = str(cur_match.group(4))
        prev_template = self.get_previous_page_template()
        if prev_template is None or prev_template.id is None:
            self.add_toc_entry(0, self.page, use_category=cur_uc)
            self.add_toc_entry(1, self.page, measure_id=cur_template.id)
            self.pt_index = self.get_current_pt_index()
            return

        prev_match = re.fullmatch(patterns.VERSION_ID, prev_template.id)
        if prev_match is None:
            self.add_toc_entry(0, self.page, use_category=cur_uc)
            self.add_toc_entry(1, self.page, measure_id=cur_template.id)
            return

        if cur_template.id != prev_template.id:
            self.add_toc_entry(0, self.page + 1, measure_id=cur_template.id)

        prev_uc = str(prev_match.group(4))
        if cur_uc != prev_uc:
            self.add_toc_entry(1, self.page + 1, use_category=cur_uc)

        self.pt_index = self.get_current_pt_index()

    def afterPage(self) -> None:
        self.after_page_toc_handler()


class SummaryPageTemplate(PageTemplate):
    def __init__(
        self,
        id: str,
        measure_name: str | None = None
    ) -> None:
        self.id = id
        self.measure_name = measure_name
        frame = Frame(
            x1=X_MARGIN,
            y1=Y_MARGIN,
            width=INNER_WIDTH,
            height=INNER_HEIGHT,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id='normal'
        )
        PageTemplate.__init__(self, id=id, frames=frame)

    def draw_footer(
        self,
        canv: Canvas,
        doc: SummaryDocTemplate
    ) -> None:
            if self.measure_name is None:
                return

            canv.saveState()

            style = PSTYLES['SmallParagraph'].bold
            id_footer = Paragraph(self.id, style=style)
            _, h = id_footer.wrap(INNER_WIDTH, Y_MARGIN)
            x = X_MARGIN / 1.5
            y = h * 1.5
            id_footer.drawOn(canvas=canv, x=x, y=y)
            id_width = stringWidth(
                self.id,
                style.font_name, 
                style.font_size
            )
            name_footer = Paragraph(
                self.measure_name,
                style=PSTYLES['SmallParagraph']
            )
            _, h = name_footer.wrap(INNER_WIDTH - id_width, Y_MARGIN)
            name_footer.drawOn(canvas=canv, x=x + id_width + 3, y=y)

            canv.restoreState()

    def draw_header(
        self,
        canv: Canvas,
        doc: SummaryDocTemplate
    ) -> None:
        canv.saveState()

        if _SYSTEM == 'Windows':
            fmt = '#'
        else:
            fmt = '-'
        cur_dt = START_TIME.strftime(rf'%{fmt}m/%{fmt}d/%y, %{fmt}I:%M%p')
        style = PSTYLES['SmallBase']
        time_header = Paragraph(cur_dt, style=style)
        _, h = time_header.wrap(INNER_WIDTH + X_MARGIN, Y_MARGIN)
        y = PAGESIZE[1] - Y_MARGIN / 2 + h / 2
        time_header.drawOn(canv, x=X_MARGIN / 1.5, y=y)

        canv.restoreState()

    def afterDrawPage(self, canv: Canvas, doc: SummaryDocTemplate) -> None:
        self.draw_footer(canv, doc)
        self.draw_header(canv, doc)


def calc_row_heights(
    data: list[list[str | Paragraph]],
    table_style: TableStyle,
    para_styles: tuple[ParagraphStyle, ...],
    base_height: float,
    base_widths: tuple[float, ...]
) -> list[float]:
    """Calculates row heights for static tables"""

    vpadding = table_style.top_padding + table_style.bottom_padding
    hpadding = table_style.left_padding + table_style.right_padding
    height = base_height + vpadding
    row_heights: list[float] = []
    row_styles: tuple[ParagraphStyle, ...] = []
    for row in data:
        row_height = height
        if isinstance(para_styles, ParagraphStyle):
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


def contains_all_climate_zones(labels: list[str]) -> bool:
    label_set = set([label.upper() for label in labels])
    for i in range(1, 17):
        if f"CZ{str(i).zfill(2)}" not in label_set:
            return False

    return True


def remove_all_climate_zones(labels: list[str]) -> None:
    if not contains_all_climate_zones(labels):
        return

    for label in reversed(labels):
        if re.fullmatch(re.compile(r"^CZ(?:(?:[0][1-9])|(?:1[0-6]))$"), label):
            labels.remove(label)


class MeasureSummary:
    """eTRM measure summary PDF generator"""

    def __init__(
        self,
        dir_path: str,
        connection: ETRMConnection,
        file_name: str = "measure_summary",
        override: bool = True
    ) -> None:
        clean()
        self.measures: dict[str, list[Measure]] = {}
        self._cur_measure: Measure | None = None
        self.connection = connection
        self.story = Story()
        self.dir_path = dir_path
        self.file_name = file_name
        if not override and os.path.exists(self.file_path):
            raise FileExistsError(f"File already exists at {self.file_path}")

        self.summary = SummaryDocTemplate(self.file_path)
        self.parser = HTMLParser()
        self.generator = FlowableGenerator()

    @property
    def dir_path(self) -> str:
        return self._dir_path

    @dir_path.setter
    def dir_path(self, path: str) -> None:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            os.mkdir(path)

        self._dir_path = path

    @property
    def file_name(self) -> str:
        return self._file_name

    @file_name.setter
    def file_name(self, name: str) -> None:
        _, ext = os.path.splitext(name)
        if ext != ".pdf":
            name += ".pdf"

        self._file_name = name

    @property
    def file_path(self) -> str:
        return os.path.join(self.dir_path, self.file_name)

    def contains(self, measure: Measure) -> bool:
        try:
            existing_measures = self.measures[measure.use_category]
            for existing_measure in existing_measures:
                if measure.full_version_id == existing_measure.full_version_id:
                    return True
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
        if len(measures) == 0:
            return False

        if measures[-1].full_version_id != measure.full_version_id:
            return False

        return True

    def is_first(self, measure: Measure) -> bool:
        if len(self.measures) == 0:
            return False

        if not self.contains(measure):
            return False

        first_uc = sorted(self.measures.keys())[0]
        if measure.use_category != first_uc:
            return False

        measures = self.measures[first_uc]
        if len(measures) == 0:
            return False

        if measures[0].full_version_id != measure.full_version_id:
            return False

        return True

    def convert_html(
        self,
        html: str,
        newline_height: float = NL_HEIGHT,
        max_width: float = INNER_WIDTH
    ) -> list[Flowable]:
        sections = self.parser.parse(
            html,
            indent_size=DEFAULT_INDENT_SIZE * (2 / 3),
            trim_newlines=True
        )
        return self.generator.generate(
            sections,
            newline_height=newline_height,
            max_width=max_width
        )

    def add_introduction(self) -> None:
        _html = resources.get_introduction_html()
        flowables = self.convert_html(_html, newline_height=DEFAULT_PARA_SPACING)
        self.story.add(Paragraph("INTRODUCTION", style=PSTYLES["h1"]))
        self.story.add(*flowables)
        self.story.add(PageBreak())

    def add_table_of_contents(self) -> None:
        self.story.add(NextPageTemplate("TOC"))
        toc_header = Paragraph("Table of Contents", style=PSTYLES["TOCHeader"])
        self.story.add(toc_header, NEWLINE)
        self.story.add(TableOfContents())
        self.story.add(PageBreak())

    def add_revision_log(self) -> None:
        logger.info("Generating revision log...")

        style = DEF_PSTYLE
        header = Paragraph("Revision Log", style=PSTYLES["h3"])
        data = []
        data.append([
            Paragraph(table_header, style.bold)
            for table_header
            in ["Version", "Publish Date", "Description of Revisions", "Owner"]
        ])
        col_widths = [INNER_WIDTH * 0.13, INNER_WIDTH * 0.2, INNER_WIDTH * 0.47, INNER_WIDTH * 0.2]
        for revision in resources.get_revisions():
            sections = self.parser.parse(
                revision.description,
                bullet_option=SQUARE_BULLET
            )
            flowables = self.generator.generate(
                sections,
                newline_height=NL_HEIGHT * 0.2,
                max_width=col_widths[2] - 8
            )
            desc_table = Table(
                [[flowable] for flowable in flowables],
                colWidths=(col_widths[2]),
                style=TSTYLES["Unstyled"]
            )
            data.append([
                Paragraph(str(revision.version), style=style),
                Paragraph(revision.publish_date.strftime(r"%Y/%m/%d"), style=style),
                desc_table,
                Paragraph(revision.owner, style=style)
            ])

        table = Table(data, colWidths=col_widths, style=TSTYLES["RevisionLog"])
        self.story.add(KeepTogether([header, table]))
        self.story.add(PageBreak())

    def add_title_page(self) -> None:
        if self._cur_measure is None:
            return

        self.story.add(TitlePage(self._cur_measure))

    def _add_value_table(self, api_name: str) -> None:
        measure_id = self._cur_measure.full_version_id
        table = self._cur_measure.get_value_table(api_name)
        if table is None:
            raise SummaryGenError(f"Missing table for {api_name} in {measure_id}")

        headers: list[str] = []
        for api_name in table.determinants:
            determinant = self._cur_measure.get_determinant(api_name)
            if determinant is None:
                raise SummaryGenError(f"Missing determinant for {api_name} in {measure_id}")

            headers.append(determinant.name)

        for column in table.columns:
            headers.append(column.name)

        data = [headers]
        for row in table.values:
            table_row: list[str] = []
            for cell in row:
                if cell is None:
                    table_row.append("")
                else:
                    table_row.append(cell)

            data.append(table_row)

        self.story.add(BasicTable(data))

    def add_bc_mc_section(self) -> None:
        measure_id = self._cur_measure.full_version_id
        desc_obj = resources.get_section_description(measure_id)
        if desc_obj is None:
            raise SummaryGenError(f"Could not find a section description for {measure_id}")

        self.story.add(
            Paragraph(
                "Measure Case and Base Case Description:",
                style=PSTYLES["h2"]
            )
        )

        self.story.add(Paragraph("Offering ID", style=PSTYLES["h4"]))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(*self.convert_html(desc_obj.offering_id))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self._add_value_table("offerId")
        self.story.add(NEWLINE)

        self.story.add(Paragraph("Base Case Description", style=PSTYLES["h4"]))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(*self.convert_html(desc_obj.base_case))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self._add_value_table("description")
        self.story.add(NEWLINE)

    def _get_shared_avg(
        self,
        param_name: str,
        column: str,
        measure: Measure
    ) -> str:
        shared_param = measure.get_shared_parameter(param_name)
        if shared_param is None:
            return ""

        try:
            table_name = lookups.SHARED_VALUE_TABLES[shared_param.name]
        except KeyError:
            return ""

        shared_lookup = measure.get_shared_lookup(table_name)
        if shared_lookup is None:
            return ""

        try:
            value_table = self.connection.get_shared_value_table(shared_lookup)
        except ETRMConnectionError:
            return ""

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
                if len(vals) == 0:
                    continue

                avg = math.fsum(vals) / len(vals)
                impacts.append(avg)
            except KeyError:
                continue

        if len(impacts) == 0:
            return ""

        impact_avg = sum(impacts) / len(impacts)
        if impact_avg == 0:
            return ""

        return f"{impact_avg:.2f}"

    def _build_parameters_table(
        self,
        params: list[tuple[str, str]],
        nd_params: list[tuple[str, str]],
    ) -> Table:
        data: list[tuple[str, str]] = [("Parameters", "Labels")]
        for verbose_name, api_name in params:
            param = self._cur_measure.get_shared_parameter(api_name)
            param_labels: list[str] = []
            if param is not None:
                labels = param.active_labels.copy()

                # Parameter specific modifications
                match param.name:
                    case "BldgLoc":
                        if contains_all_climate_zones(labels):
                            remove_all_climate_zones(labels)
                            param_labels.append("All climate zones")
                    case _:
                        pass

                for label in labels:
                    desc = self.connection.get_shared_parameter_description(
                        param.name,
                        param.version,
                        label
                    )
                    param_labels.append(f"{label} - {desc}")

            data.append((verbose_name, ", ".join(param_labels).strip()))

        for verbose_name, api_name in nd_params:
            param = self._cur_measure.get_shared_parameter(api_name)
            data.append((verbose_name, ", ".join(param.active_labels).strip()))

        return BasicTable(data)

    def add_parameters_table(self) -> None:
        if self._cur_measure is None:
            return

        params = [
            ("Measure Application Type", "MeasAppType"),
            ("Sector", "Sector"),
            ("Building Type", "BldgType"),
            ("Building Vintage", "BldgVint"),
            ("Building Location", "BldgLoc"),
            ("Delivery Type", "DelivType"),
            ("Normalized Unit", "NormUnit")
        ]

        nd_params = [
            ("Electric Impact Profile ID", "electricImpactProfileID"),
            ("Gas Impact Profile ID", "GasImpactProfileID")
        ]

        table = self._build_parameters_table(params, nd_params)
        table_header = Paragraph("Applicable Parameters:", PSTYLES["h2"])
        self.story.add(KeepTogether([table_header, table]), NEWLINE)

    def add_impact_table(self):
        if self._cur_measure is None:
            return

        try:
            perms = self.connection.get_permutations(self._cur_measure)
        except ETRMResponseError as err:
            raise SummaryGenError(f"eTRM Connection Error ({err.status}):\n{err.message}")

        cost_map = {
            "pre_pedr": perms.get_existing_pedr(),
            "std_pedr": perms.get_standard_pedr(),
            "pre_es": perms.get_existing_es(),
            "std_es": perms.get_standard_es(),
            "pre_gs": perms.get_existing_gs(),
            "std_gs": perms.get_standard_gs(),
            "pre_ws": perms.get_existing_ws(),
            "std_ws": perms.get_standard_ws(),
            "msr_cost": perms.get_measure_cost(),
            "inc_cost": perms.get_incremental_cost(),
            "bsc_cost": perms.get_base_case_cost(),
            "eul_yrs": perms.get_eul_years(),
            "rul_yrs": perms.get_rul_years()
        }

        for key, val in cost_map.items():
            if val is None:
                cost_map[key] = "-"
            elif key != "eul_yrs" and key != "rul_yrs":
                cost_map[key] = f"{val:.2f}"
            else:
                cost_map[key] = f"{int(val)}"

        measure_id, version = self._cur_measure.full_version_id.split("-", 1)
        base_link = f"{ETRM_URL}/measure/{measure_id.lower()}/{version}/"
        link_map = {
            "pedr": f"{base_link}#peak-electric-demand-reduction-kw",
            "es": f"{base_link}#electric-savings-kwh",
            "gs": f"{base_link}#gas-savings-therms",
            "ws": f"{base_link}#non-energy-impacts",
            "costs": f"{base_link}#base-case-material-cost-unit",
            "life": f"{base_link}#life-cycle"
        }

        data = [
            ["", "Average Value", "Methodology"],
            [
                "Existing - Peak Demand Reduction (kW)",
                cost_map.get("pre_pedr"),
                Paragraph(
                    f"<link href=\"{link_map.get('pedr')}\">Link</link>",
                    style=DEF_PSTYLE.link
                )
            ],
            ["Standard - Peak Demand Reduction (kW)", cost_map.get("std_pedr"), ""],
            [
                "Existing - Electric Savings (kWh/yr)",
                cost_map.get("pre_es"),
                Paragraph(
                    f"<link href=\"{link_map.get('es')}\">Link</link>",
                    style=DEF_PSTYLE.link
                )
            ],
            ["Standard - Electric Savings (kWh/yr)", cost_map.get("std_es"), ""],
            [
                "Existing - Gas Savings (therm/yr)",
                cost_map.get("pre_gs"),
                Paragraph(
                    f"<link href=\"{link_map.get('gs')}\">Link</link>",
                    style=DEF_PSTYLE.link
                )
            ],
            ["Standard - Gas Savings (therm/yr)", cost_map.get("std_gs"), ""],
            [
                "Existing - Water Savings (gal/yr)",
                cost_map.get("pre_ws"),
                Paragraph(
                    f"<link href=\"{link_map.get('ws')}\">Link</link>",
                    style=DEF_PSTYLE.link
                )
            ],
            ["Standard - Water Savings (gal/yr)", cost_map.get("std_ws"), ""],
            [
                "Measure Case Costs ($)",
                cost_map.get("msr_cost"),
                Paragraph(
                    f"<link href=\"{link_map.get('costs')}\">Link</link>",
                    style=DEF_PSTYLE.link
                )
            ],
            ["Base Case Costs ($)", cost_map.get("bsc_cost"), ""],
            ["Incremental Cost ($)", cost_map.get("inc_cost"), ""],
            [
                "Effective Useful Life (years)",
                cost_map.get("eul_yrs"),
                Paragraph(
                    f"<link href=\"{link_map.get('life')}\">Link</link>",
                    style=DEF_PSTYLE.link
                )
            ],
            ["Remaining Useful Life (years)", cost_map.get("rul_yrs"), ""]
        ]

        spans = [
            ((1, 2), (2, 0)),
            ((3, 2), (2, 0)),
            ((5, 2), (2, 0)),
            ((7, 2), (2, 0)),
            ((9, 2), (3, 0)),
            ((12, 2), (2, 0))
        ]
        table = BasicTable(data, spans=spans)
        header = Paragraph("Average Impact:", style=PSTYLES["h2"])
        self.story.add(KeepTogether([header, table]), NEWLINE)

    def add_streamlined_permutations(self) -> None:
        file_name = f"SW{self._cur_measure.use_category.upper()}_Summary.xlsx"
        self.story.add(Paragraph("Streamlined Permutations:", style=PSTYLES["h5"]))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(
            ExcelLink(
                file_name,
                "https://google.com"
            )
        )

    def get_shared_key_terminology_table(self, item: KeyTerminology) -> list[list[str]]:
        if not item.requires_etrm_table():
            return []

        if item.api_name is None or item.columns is None:
            raise SummaryGenError(f"Incorrectly required eTRM table for {item.name}")

        table_content: list[list[str]] = []
        param = self.connection.get_shared_parameter(item.api_name)
        for label in param.labels:
            row: list[str] = []
            for col_name in item.columns:
                try:
                    content = getattr(label, col_name)
                except AttributeError:
                    raise SummaryGenError(
                        f"Label for {param.name} does not have a {col_name} attribute"
                    )

                row.append(content)

            table_content.append(row)

        return table_content

    def get_static_key_terminology_table(self, item: KeyTerminology) -> list[list[Flowable]]:
        """Parses the static table from `item` and returns a matrix that can
        be used to build a reportlab Table flowable.

        Raises:
            - SummaryGenError
                : `item` does not contain a static data table.
        """

        if item.data is None:
            raise SummaryGenError(
                f"Key terminology for {item.name} does not contain a static table"
            )

        static_content: list[list[Flowable]] = []
        for row in item.data:
            row_content: list[Flowable] = []
            for cell in row:
                sections = self.parser.parse(cell)
                flowables = self.generator.generate(sections, newline_height=NL_HEIGHT * 0.1)
                if flowables == []:
                    row_content.append(Paragraph(""))
                else:
                    widths = []
                    heights = []
                    for flowable in flowables:
                        widths.append(get_flowable_width(flowable))
                        heights.append(get_flowable_height(flowable))

                    row_content.append(
                        Table(
                            data=[[flowable] for flowable in flowables],
                            hAlign="LEFT",
                            style=TSTYLES["Unstyled"],
                            colWidths=[max(widths)],
                            rowHeights=heights
                        )
                    )

            static_content.append(row_content)

        return static_content

    def split_kt_table_data(self, data: list[list[_T]], row_split: int) -> list[list[_T]]:
        """Applies row splits to the key terminology data by breaking up the
        table into `len(data) // row_split` columns.

        I probably should have specified the number of columns instead, but
        whatever.
        """

        split_data: list[list[_T]] = []
        for _ in range(row_split):
            split_data.append([])

        for i, row in enumerate(data):
            split_data[i % row_split].extend(row)

        # Fill any empty table cells
        max_length = max([len(row) for row in split_data])
        for row in split_data:
            if len(row) < max_length:
                row.extend([""] * (max_length - len(row)))

        return split_data

    def add_key_terminology_table(self, item: KeyTerminology, indents: int = 0) -> None:
        """Adds a table to the key terminology section for `item`.

        Raises:
            - SummaryGenError
                : No table headers were provided in the JSON file
        """

        headers = item.get_table_headers()
        if headers is None:
            raise SummaryGenError(f"Cannot generate a table for {item.name} without headers")

        max_width = INNER_WIDTH - indents * DEFAULT_INDENT_SIZE
        data = self.get_shared_key_terminology_table(item)
        if item.data is not None:
            static_data = self.get_static_key_terminology_table(item)
            if item.append == "before":
                data = [*static_data, *data]
            elif item.append == "after":
                data.extend(static_data)
            else:
                data = static_data

        if item.row_split is None:
            num_cols = 1
        else:
            num_cols = math.ceil(len(data) / item.row_split)

        if item.row_split is not None:
            data = self.split_kt_table_data(data, item.row_split)

        if data == []:
            return

        data.insert(0, headers * num_cols)
        self.story.add(
            BasicTable(
                data=data,
                header_styles=DEF_PSTYLE.bold,
                body_col_styles=DEF_PSTYLE,
                table_style=get_key_terminology_table_style(num_cols, len(headers)),
                max_width=max_width - 10,
                min_col_widths=True,
                h_align="center",
                x_padding=10,
                y_padding=3
            )
        )
        self.story.add(NEWLINE)

    def add_key_terminology_caption(self, item: KeyTerminology) -> None:
        sections = self.parser.parse(f"<em>{item.caption}</em>")
        flowables = self.generator.generate(sections, newline_height=DEFAULT_PARA_SPACING)
        self.story.add(*flowables)

    def add_key_terminology_item(self, item: KeyTerminology, indents: int = 0) -> None:
        logger.info(f"Generating key terminology section for {item.name}...")

        content = f"<kth>{item.name}: </kth>{item.content}"
        sections = self.parser.parse(content, indents=indents)
        flowables = self.generator.generate(sections, newline_height=DEFAULT_PARA_SPACING)
        self.story.add(*flowables)
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        if item.contains_table:
            self.add_key_terminology_table(item, indents=indents)

        if item.caption is not None:
            self.add_key_terminology_caption(item)
            self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))

        if item.sub_sections != None:
            for sub_section in item.sub_sections:
                self.add_key_terminology_item(sub_section, indents=indents + 1)

    def add_key_terminology(self) -> None:
        logger.info("Generating key terminology sections...")

        self.story.add(Paragraph("KEY TERMINOLOGY", style=PSTYLES["h1"]))
        key_terminology = resources.get_key_terminology()
        sections = self.parser.parse(key_terminology.introduction)
        flowables = self.generator.generate(sections, newline_height=DEFAULT_PARA_SPACING)
        self.story.add(*flowables, Spacer(0.01, DEFAULT_PARA_SPACING))

        for terminology_item in key_terminology.items:
            self.add_key_terminology_item(terminology_item)

        self.story.add(PageBreak())

    def add_data_table(self) -> None:
        logger.info("Adding the data table...")

        self.story.add(Paragraph("DATA TABLE", style=PSTYLES["h1"]))
        _html = resources.get_data_table_html()
        self.story.add(*self.convert_html(_html, newline_height=DEFAULT_PARA_SPACING))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(
            Paragraph(
                "eTRM Data Specification",
                style=PSTYLES["h3"]
            )
        )

        self.story.add(
            ExcelLink(
                "eTRM - Data Specification.xls",
                "https://google.com"
            )
        )

        self.story.add(PageBreak())

    def add_spreadsheets(self) -> None:
        self.story.add(
            Paragraph(
                "Permutations Summary Spreadsheets",
                style=PSTYLES["h3"]
            )
        )

        for use_category, _ in lookups.USE_CATEGORIES.items():
            self.story.add(
                ExcelLink(
                    f"SW{use_category}_Summary.xlsx",
                    "https://google.com"
                )
            )
            self.story.add(Spacer(0.01, 8))

        self.story.add(PageBreak())

    def add_sunsetted_measures(self) -> None:
        section = resources.get_sunsetted_measures()
        flowables = self.convert_html(section.introduction, newline_height=DEFAULT_PARA_SPACING)
        self.story.add(*flowables)
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(SunsettedMeasuresTable(section.use_categories))
        self.story.add(PageBreak())

    def add_appendix(self) -> None:
        self.story.add(Paragraph("APPENDIX", style=PSTYLES["h1"]))
        self.add_spreadsheets()
        self.add_sunsetted_measures()

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
            try:
                measure = self.connection.get_measure(arg)
            except ETRMResponseError as err:
                raise SummaryGenError(f'eTRM Connection Error ({err.status})'
                                      f'\n{err.message}')
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

    def add_use_category(self, use_category: str) -> None:
        """Adds the most recent published version of each measure in the
        use category `use_category`.

        Use when making a summary of a use category.
        """

        logger.info(f'Adding use category {use_category}')

        connection = self.connection
        try:
            measure_ids = connection.get_all_measure_ids(use_category)
        except ETRMResponseError as err:
            raise SummaryGenError(f'eTRM Connection Error ({err.status}):'
                                  f'\n{err.message}')

        versions: list[str] = []
        for measure_id in measure_ids:
            try:
                measure_versions = connection.get_measure_versions(measure_id)
            except ETRMResponseError as err:
                raise SummaryGenError(f'eTRM Connection Error ({err.status}):'
                                      f'\n{err.message}')

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

    def filter_measures(
        self,
        min_end_date: datetime.date | None = None
    ) -> None:
        """Filters the currently stored measures to meet the parameters.
        
        Parameters:
            `min_end_date` - A date representing the earliest the end date
            of a measure can be. Any measures without an end date will still
            be permitted.
        """

        # flattens the dict of measure lists
        measures = [
            measure
                for measures
                in self.measures.values()
                for measure
                in measures
        ]

        self.measures = {}
        for measure in measures:
            end_date = measure.end_date
            if not (min_end_date is None
                    or end_date is None
                    or end_date >= min_end_date):
                continue

            self.add_measure(measure)

    def reset(self):
        self.story.clear()

    def _build_summary(self, measure: Measure | None = None) -> None:
        if measure is None:
            if self._cur_measure is None:
                raise SummaryGenError("Cannot generate a summary without a measure")

            summary_measure = self._cur_measure
        else:
            summary_measure = measure
            self._cur_measure = measure

        logger.info(f"Building summary for measure {summary_measure.full_version_id}")

        template = SummaryPageTemplate(
            id=summary_measure.full_version_id,
            measure_name=summary_measure.name
        )
        self.summary.addPageTemplates(template)
        self.story.add(NextPageTemplate(summary_measure.full_version_id))

        self.add_title_page()
        self.add_bc_mc_section()
        self.add_parameters_table()
        self.add_impact_table()
        self.add_streamlined_permutations()
        self.story.add(PageBreak())

        self._cur_measure = None

    def build(self, toc: bool = False) -> None:
        self.add_introduction()
        self.add_revision_log()
        if toc:
            self.add_table_of_contents()

        for use_category in sorted(self.measures.keys()):
            for measure in self.measures[use_category]:
                self._build_summary(measure)

        self.add_key_terminology()
        self.add_data_table()
        self.add_appendix()
        if self.story.contents == []:
            raise RuntimeError("Cannot create an empty summary")

        self.summary.multiBuild(self.story.contents, canvasmaker=NumberedCanvas)
        clean()
