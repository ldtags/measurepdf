import os
import re
import csv
import math
import shutil
import logging
import xlsxwriter as xl
from typing import TypeVar
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
from reportlab.platypus.frames import Frame

from src import (
    lookups,
    patterns,
    resources,
    _SYSTEM,
    START_TIME,
    TMP_DIR
)
from src.etrm import ETRM_URL
from src.etrm.models import Measure, ValueTable
from src.etrm.connection import ETRMConnection
from src.etrm.exceptions import (
    ETRMConnectionError,
    ETRMResponseError
)
from src.resources import KeyTerminology
from src.summarygen.utils import get_flowable_height, get_flowable_width
from src.summarygen.models import Story, SQUARE_BULLET
from src.summarygen.styles import (
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
    SunsettedMeasuresTable,
    TableOfContents,
    CoverPage
)
from src.summarygen.exceptions import SummaryGenError


logger = logging.getLogger(__name__)

_T = TypeVar("_T")

_conn: ETRMConnection | None = None

DATA_TABLE_FOLDER_NAME = "data_tables"


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
        self._use_categories: set[str] = set()
        self._prev_measure_id: str | None = None
        self._first_measure_id: str | None = None

    def get_page_template(self, id: str) -> PageTemplate | None:
        for page_template in self.pageTemplates:
            if page_template.id == id:
                return page_template

        return None

    def add_use_category_toc_entry(self, use_category: str, is_first: bool) -> None:
        full_name = lookups.USE_CATEGORIES.get(use_category)
        if full_name is not None:
            text = f"{full_name} - {use_category}"
        else:
            text = use_category

        self._use_categories.add(use_category)
        self.notify("TOCEntryUC", (text, self.page + 1, is_first))

    def add_measure_toc_entry(self, version_id: str) -> None:
        res = False
        mfc = False
        nonres = False
        global _conn
        if _conn is None:
            measure_name = ""
            active_life = ""
        else:
            measure = _conn.get_measure(version_id)
            measure_name = measure.name
            start_date = measure.start_date.strftime(r"%Y-%m-%d")
            if measure.end_date is None:
                end_date = "Unknown"
            else:
                end_date = measure.end_date.strftime(r"%Y-%m-%d")

            active_life = f"{start_date} - {end_date}"
            bldg_type = measure.get_shared_parameter("BldgType")
            blt_labels = set([label.lower() for label in bldg_type.active_labels])
            if "mfmcmn" in blt_labels:
                mfc = True

            sector = measure.get_shared_parameter("sector")
            sec_labels = set([label.lower() for label in sector.active_labels])
            if "res" in sec_labels and blt_labels != {"mfmcmn"}:
                res = True

            nonres_labels = {"com", "ind", "ag"}
            if sec_labels.intersection(nonres_labels) != set():
                nonres = True

        self._prev_measure_id = version_id
        if self._first_measure_id is None:
            self._first_measure_id = version_id

        self.notify(
            "TOCEntryM",
            (
                version_id,
                self.page + 1,
                measure_name,
                active_life,
                res,
                mfc,
                nonres
            )
        )

    def add_generic_toc_entry(self, id: str) -> None:
        match id:
            case "key_terminology":
                text = "Key Terminology"
                key = "TOCEntryUC"
            case "data_table":
                text = "Data Table"
                key = "TOCEntryUC"
            case "appendix":
                text = "Appendix"
                key = "TOCEntryUC"
            case "data_spec":
                text = "eTRM Data Specification"
                key = "TOCEntry"
            case "summary_spreadsheets":
                text = "Permutations Summary Spreadsheets"
                key = "TOCEntry"
            case "sunsetted_measures":
                text = "Sunsetted or Deactivated Measures"
                key = "TOCEntry"
            case _:
                return

        stuff = (text, self.page + 1)
        if key == "TOCEntryUC":
            stuff = (*stuff, False)

        self.notify(key, stuff)
        if id == "appendix":
            self.add_generic_toc_entry("summary_spreadsheets")

    def _is_first_uc(self, version_id: str) -> bool:
        if self._first_measure_id is None:
            return True

        return version_id == self._first_measure_id

    def _should_add_use_category(self, version_id: str) -> bool:
        re_match = re.fullmatch(patterns.VERSION_ID, version_id)
        if re_match is None:
            return False

        if self._prev_measure_id is None:
            return True

        use_category = str(re_match.group(4))
        measure_type = int(re_match.group(5))
        version_num = int(re_match.group(6))

        re_match = re.fullmatch(patterns.VERSION_ID, self._prev_measure_id)
        if re_match is None:
            return False

        prev_use_category = str(re_match.group(4))
        prev_measure_type = int(re_match.group(5))
        prev_version_num = int(re_match.group(6))

        if prev_use_category != use_category:
            return True

        if measure_type < prev_measure_type:
            return True
        elif measure_type > prev_measure_type:
            return False

        if version_num > prev_version_num:
            return False

        return True

    def afterFlowable(self, flowable: Flowable) -> None:
        if not isinstance(flowable, NextPageTemplate):
            return

        try:
            template_id = str(flowable.action[1])
        except ValueError:
            raise SummaryGenError(f"Invalid template id: {flowable.action[1]}")

        if template_id.lower() == "swfs001-03":
            pass

        re_match = re.fullmatch(patterns.VERSION_ID, template_id)
        if re_match is None:
            self.add_generic_toc_entry(template_id)
            return

        try:
            use_category = str(re_match.group(4))
        except ValueError as err:
            raise SummaryGenError(f"Invalid use category: {re_match.group(4)}") from err

        if self._should_add_use_category(template_id):
            self.add_use_category_toc_entry(use_category, self._is_first_uc(template_id))

        self.add_measure_toc_entry(template_id)


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
            id="normal"
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

            # draw measure ID
            style = PSTYLES["SmallParagraph"].bold
            id_footer = Paragraph(self.id, style=style)
            _, h = id_footer.wrap(INNER_WIDTH, Y_MARGIN)
            x = X_MARGIN / 1.5
            y = h * 1.5
            id_footer.drawOn(canvas=canv, x=x, y=y)

            # draw measure name
            id_width = stringWidth(
                self.id,
                style.font_name, 
                style.font_size
            )
            name_footer = Paragraph(
                self.measure_name,
                style=PSTYLES["SmallParagraph"]
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

        if _SYSTEM == "Windows":
            fmt = "#"
        else:
            fmt = "-"

        # draw date and time
        cur_dt = START_TIME.strftime(rf"%{fmt}m/%{fmt}d/%y, %{fmt}I:%M%p")
        style = PSTYLES["SmallBase"]
        time_header = Paragraph(cur_dt, style=style)
        _, h = time_header.wrap(INNER_WIDTH + X_MARGIN, Y_MARGIN)
        y = PAGESIZE[1] - Y_MARGIN / 2 + h / 2
        time_header.drawOn(canv, x=X_MARGIN / 1.5, y=y)

        canv.restoreState()

    def afterDrawPage(self, canv: Canvas, doc: SummaryDocTemplate) -> None:
        self.draw_footer(canv, doc)
        self.draw_header(canv, doc)


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


def tables_need_splitting(*tables: BasicTable) -> bool:
    total_height: float = 0
    for table in tables:
        table_height = math.fsum(table._argH)
        if table_height >= INNER_HEIGHT:
            return True

        total_height += table_height

    if total_height >= INNER_HEIGHT * 2:
        return True

    return False


def sanitize_value_table_row(row: list[str | None]) -> list[str]:
    sanitized_row: list[str] = []
    for item in row:
        if item is None:
            sanitized_row.append("")
        else:
            sanitized_row.append(item)

    return sanitized_row


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
        os.mkdir(TMP_DIR)
        self.measures: dict[str, list[Measure]] = {}
        self._cur_measure: Measure | None = None
        self.story = Story()
        self.dir_path = dir_path
        self.file_name = file_name
        if not override and os.path.exists(self.file_path):
            raise FileExistsError(f"File already exists at {self.file_path}")

        global _conn
        _conn = self.connection = connection

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

    def add_table_of_contents(self) -> None:
        toc_header = Paragraph("TABLE OF CONTENTS", style=PSTYLES["h1"])
        self.story.add(toc_header, Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(TableOfContents())

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

    def add_title_page(self) -> None:
        if self._cur_measure is None:
            return

        self.story.add(TitlePage(self._cur_measure))

    def _get_value_table(self, *api_names: str) -> ValueTable:
        measure_id = self._cur_measure.full_version_id
        table = None
        for api_name in api_names:
            table = self._cur_measure.get_value_table(api_name)
            if table is not None:
                break

        if table is None:
            raise SummaryGenError(f"Missing table for {api_name} in {measure_id}")

        return table

    def _get_value_table_data(self, table: ValueTable) -> list[list[str]]:
        measure_id = self._cur_measure.full_version_id
        headers: list[str] = []
        for api_name in table.determinants:
            determinant = self._cur_measure.get_determinant(api_name)
            if determinant is None:
                determinant = self._cur_measure.get_shared_parameter(api_name)

            if determinant is None:
                raise SummaryGenError(
                    f"Missing determinant for {api_name} in measure {measure_id}"
                )

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

        return data

    def _build_value_table(self, table: ValueTable) -> BasicTable:
        data = self._get_value_table_data(table)
        return BasicTable(data)

    def _add_to_data_table(self, offer_table: ValueTable, desc_table: ValueTable) -> None:
        headers: list[str] = [
            "Offering ID",
            "Offering Description",
            "Existing Description",
            "Standard Description"
        ]

        for api_name in offer_table.determinants:
            name = self._cur_measure.get_full_determinant_name(api_name)
            if name is None:
                name = "Unknown"

            headers.append(name)

        # assumes the following:
        #   - tables have the same amount of values
        #   - table rows are properly lined up
        #   - tables have the same determinants
        data: list[list[str]] = []
        for i in range(len(offer_table.values)):
            data_row: list[str] = []
            offer_row = sanitize_value_table_row(offer_table.values[i])
            for item in offer_row[len(offer_table.determinants):]:
                data_row.append(item)

            desc_row = sanitize_value_table_row(desc_table.values[i])
            for j, item in enumerate(desc_row[len(desc_table.determinants):]):
                if desc_table.columns[j].api_name == "ID":
                    continue

                data_row.append(item)

            for item in offer_row[:len(offer_table.determinants)]:
                data_row.append(item)

            data.append(data_row)

        folder_path = os.path.join(TMP_DIR, DATA_TABLE_FOLDER_NAME)
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

        measure_id = self._cur_measure.full_version_id
        with open(os.path.join(folder_path, measure_id + ".csv"), "w+", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow({
                    key: val
                    for (key, val)
                    in zip(headers, row)
                })

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

        overly_large = False
        offer_value_table = self._get_value_table("offerId")
        offer_table = self._build_value_table(offer_value_table)
        desc_value_table = self._get_value_table("description", "Desc")
        desc_table = self._build_value_table(desc_value_table)
        if tables_need_splitting(offer_table, desc_table):
            overly_large = True
            self._add_to_data_table(offer_value_table, desc_value_table)

        self.story.add(Paragraph("Offering ID", style=PSTYLES["h4"]))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(*self.convert_html(desc_obj.offering_id))
        if not overly_large:
            self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
            self.story.add(offer_table)

        self.story.add(NEWLINE)

        self.story.add(Paragraph("Base Case Description", style=PSTYLES["h4"]))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(*self.convert_html(desc_obj.base_case))
        if not overly_large:
            self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
            self.story.add(desc_table)

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
        file_name = rf"SW{self._cur_measure.use_category.upper()}_Summary.xlsx"
        self.story.add(Paragraph("Streamlined Permutations:", style=PSTYLES["h5"]))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(ExcelLink(file_name, file_name))

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

        file_name = "eTRM - Data Tables.xlsx"
        self.story.add(ExcelLink(file_name, file_name))

    def add_spreadsheets(self) -> None:
        self.story.add(
            Paragraph(
                "Permutations Summary Spreadsheets",
                style=PSTYLES["h3"]
            )
        )

        _html = resources.get_use_category_intro_html()
        self.story.add(*self.convert_html(_html, newline_height=DEFAULT_PARA_SPACING))
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        data: list[list] = []
        style = DEF_PSTYLE
        max_text_width = 0
        for use_category, _ in lookups.USE_CATEGORIES.items():
            file_name = f"SW{use_category}_Summary.xlsx"
            full_name = lookups.USE_CATEGORIES.get(use_category)
            if full_name is None:
                full_name = f"SW{use_category}"
            else:
                full_name += f" - SW{use_category}"

            full_name += ":"
            text_width = stringWidth(full_name, style.font_name, style.font_size)
            max_text_width = max(max_text_width, text_width)
            data.append([
                Paragraph(full_name, style=style),
                ExcelLink(file_name, file_name)
            ])

        style = TSTYLES["PermutationsSummarySpreadsheet"]
        padx = style.left_padding + style.right_padding
        self.story.add(Table(
            data,
            style=style,
            hAlign="LEFT",
            colWidths=[max_text_width + padx, INNER_WIDTH - max_text_width - padx]
        ))

    def add_data_spec(self) -> None:
        self.story.add(
            Paragraph(
                "Permutation Data Specification",
                style=PSTYLES["h3"]
            )
        )

        file_name = "eTRM - Data Specification.xls"
        self.story.add(ExcelLink(file_name, file_name))

    def add_sunsetted_measures(self) -> None:
        section = resources.get_sunsetted_measures()
        flowables = self.convert_html(section.introduction, newline_height=DEFAULT_PARA_SPACING)
        self.story.add(*flowables)
        self.story.add(Spacer(0.01, DEFAULT_PARA_SPACING))
        self.story.add(SunsettedMeasuresTable(section.use_categories))

    def add_appendix(self) -> None:
        self.story.add(Paragraph("APPENDIX", style=PSTYLES["h1"]))
        self.add_spreadsheets()
        self.story.add(NextPageTemplate("data_spec"), PageBreak())
        self.add_data_spec()
        self.story.add(NextPageTemplate("sunsetted_measures"), PageBreak())
        self.add_sunsetted_measures()

    def add_measure(self, measure: Measure) -> None:
        logger.info(f"Adding measure {measure.full_version_id}")
        try:
            self.measures[measure.use_category].append(measure)
            self.measures[measure.use_category].sort(key=Measure.sorting_key)
        except KeyError:
            self.measures[measure.use_category] = [measure]

    def reset(self):
        self.story.clear()

    def _add_measure_template(self, measure: Measure) -> None:
        template = SummaryPageTemplate(
            id=measure.full_version_id,
            measure_name=measure.name
        )
        self.summary.addPageTemplates(template)
        self.story.add(NextPageTemplate(measure.full_version_id))

    def build_summary(self, measure: Measure | None = None) -> None:
        if measure is None:
            if self._cur_measure is None:
                raise SummaryGenError("Cannot generate a summary without a measure")

            summary_measure = self._cur_measure
        else:
            summary_measure = measure
            self._cur_measure = measure

        logger.info(f"Building summary for measure {summary_measure.full_version_id}")

        self.add_title_page()
        self.add_bc_mc_section()
        self.add_parameters_table()
        self.add_impact_table()
        self.add_streamlined_permutations()

        self._cur_measure = None

    def _add_default_page_templates(self) -> None:
        self.summary.addPageTemplates([
            SummaryPageTemplate(id="default"),
            SummaryPageTemplate(id="key_terminology"),
            SummaryPageTemplate(id="data_table"),
            SummaryPageTemplate(id="appendix"),
            SummaryPageTemplate(id="data_spec"),
            SummaryPageTemplate(id="sunsetted_measures")
        ])

    def build_data_table(self) -> None:
        folder_path = os.path.join(TMP_DIR, DATA_TABLE_FOLDER_NAME)
        if not os.path.exists(folder_path):
            return

        wb_path = "summaries/eTRM_Data_Specification.xlsx"
        if os.path.exists(wb_path):
            os.remove(wb_path)

        with xl.Workbook(wb_path) as wb:
            align_right_fmt = wb.add_format()
            align_right_fmt.set_align("right")
            for file_name in os.listdir(folder_path):
                version_id, ext = os.path.splitext(file_name)
                if ext != ".csv":
                    continue

                headers: list[str] = []
                data: list[list[str]] = []
                with open(os.path.join(folder_path, file_name), "r", newline="") as fp:
                    reader = csv.reader(fp)
                    for i, row in enumerate(reader):
                        if i == 0:
                            headers.extend(row)
                        else:
                            data.append(row)

                ws = wb.add_worksheet(version_id)
                measure = self.connection.get_measure(version_id)
                ws.write_string(0, 0, "Statewide Measure ID:", align_right_fmt)
                ws.write_string(0, 1, measure.statewide_measure_id)
                ws.write_string(1, 0, "Measure Version ID:", align_right_fmt)
                ws.write_string(1, 1, measure.full_version_id)
                ws.write_string(2, 0, "Measure Name:", align_right_fmt)
                ws.write_string(2, 1, measure.name)
                ws.add_table(
                    *(3, 0, len(data) + 3, len(headers) - 1),
                    {
                        "columns": [
                            {"header": header} for header in headers
                        ],
                        "data": data
                    }
                )
                ws.autofit()
                ws.ignore_errors({"number_stored_as_text": f"C3:P{len(data)}"})

    def build(self, toc: bool = True) -> None:
        self.story.add(CoverPage())
        self.story.add(PageBreak())
        self._add_default_page_templates()
        self.story.add(NextPageTemplate("default"))

        self.add_introduction()
        self.story.add(PageBreak())
        self.add_revision_log()
        if toc:
            self.story.add(PageBreak())
            self.add_table_of_contents()

        sorted_measures: list[Measure] = []
        for use_category in sorted(self.measures.keys()):
            for measure in self.measures[use_category]:
                sorted_measures.append(measure)

        if sorted_measures != []:
            self._add_measure_template(sorted_measures[0])
            self.story.add(PageBreak())
            for i, measure in enumerate(sorted_measures):
                if resources.get_section_description(measure.full_version_id) is None:
                    continue

                self.build_summary(measure)
                if i != len(sorted_measures) - 1:
                    self._add_measure_template(sorted_measures[i + 1])
                else:
                    self.story.add(NextPageTemplate("key_terminology"))

                self.story.add(PageBreak())

        self.add_key_terminology()
        self.story.add(NextPageTemplate("data_table"), PageBreak())
        self.add_data_table()
        self.story.add(NextPageTemplate("appendix"), PageBreak())
        self.add_appendix()
        if self.story.contents == []:
            raise RuntimeError("Cannot create an empty summary")

        self.build_data_table()
        self.summary.multiBuild(self.story.contents, canvasmaker=NumberedCanvas)
        clean()
