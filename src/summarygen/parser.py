from __future__ import annotations
import requests
import shutil
import os
import copy
import math
from bs4 import (
    BeautifulSoup,
    Tag,
    NavigableString,
    ResultSet,
    PageElement
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    ListFlowable,
    ListItem,
    Spacer,
    KeepTogether,
    Image,
    XPreformatted
)

from src import _ROOT
from src.etrm import ETRM_URL, ETRMConnection
from src.etrm.models import Measure, ValueTable
from src.exceptions import (
    SummaryGenError,
    WidthExceededError
)
from src.summarygen.types import _TABLE_SPAN
from src.summarygen.models import (
    ParagraphElement,
    ReferenceTag,
    EmbeddedValueTableTag,
    TextStyle,
    EmbeddedImage,
    ElemType
)
from src.summarygen.styling import (
    BetterTableStyle,
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES,
    INNER_WIDTH,
    INNER_HEIGHT,
    PAGESIZE,
    get_table_style,
    BetterParagraphStyle
)
from src.summarygen.flowables import (
    TableCell,
    Reference,
    ValueTableHeader,
    ElementLine,
    ParagraphLine,
    NEWLINE
)


class FlowableList:
    def __init__(self,
                 inner_height: float=INNER_HEIGHT,
                 inner_width: float=INNER_WIDTH):
        self.inner_height = inner_height
        self.inner_width = inner_width
        self.flowables: list[Flowable] = []
        self.current_height: float=0

    @property
    def avail_height(self) -> float:
        return self.inner_height - self.current_height

    def get_height(self, flowable: Flowable) -> float:
        if isinstance(flowable, KeepTogether | ListFlowable):
            height = 0
            for item in flowable._content:
                height += self.get_height(item)
        else:
            _, height = flowable.wrap(0, 0)
        return height

    def can_fit(self, *flowables: Flowable) -> bool:
        height = 0
        for flowable in flowables:
            height += self.get_height(flowable)
        return height <= self.avail_height

    def add(self, *flowables: Flowable):
        for flowable in flowables:
            height = self.get_height(flowable)
            if not self.can_fit(flowable):
                self.current_height = 0
            self.current_height += height
            self.flowables.append(flowable)

    def clear(self):
        self.flowables = []
        self.current_height = 0


TMP_DIR = os.path.join(_ROOT, 'assets', 'images', 'tmp')

HDR_TAGS = ['h3', 'h6']

EMB_ATTRS = ['data-etrmreference',
             'data-etrmvaluetable',
             'data-etrmcalculation',
             'data-omboimage']


def is_embedded(tag: Tag) -> bool:
    return set(EMB_ATTRS).intersection(set(tag.attrs.keys())) != set()


def is_header(element: PageElement) -> bool:
    return (isinstance(element, Tag)
        and element.name in HDR_TAGS
        and element.next_sibling != None)


def _parse_element(element: PageElement) -> list[ParagraphElement]:
    """Converts a `PageElement` object into a list of `ParagraphElement`
    objects.
    """

    if isinstance(element, NavigableString):
        return [ParagraphElement(element.get_text())]

    if not isinstance(element, Tag):
        raise RuntimeError(f'unsupported page element: {element}')

    match element.name:
        case 'p':
            elements = _parse_elements(element.contents)
            return elements
        case 'th' | 'td' | 'li':
            return _parse_elements(element.contents)
        case 'div' | 'span':
            json_str = element.attrs.get('data-etrmreference', None)
            if json_str != None:
                return [ReferenceTag(json_str)]
            return _parse_elements(element.contents)
        case 'strong' | 'sup' | 'sub' | 'em':
            elements = _parse_elements(element.contents)
            for item in elements:
                style = TextStyle(element.name)
                if style not in item.styles:
                    item.styles.insert(0, style)
            return elements
        case 'br':
            return [ParagraphElement('', type=ElemType.NEWLINE)]
        case _:
            raise RuntimeError(f'unsupported tag: {element.name}')


def _parse_elements(elements: list[PageElement]) -> list[ParagraphElement]:
    contents: list[ParagraphElement] = []
    for element in elements:
        parsed_elements = _parse_element(element)
        if parsed_elements != None:
            contents.extend(parsed_elements)
    return contents


def get_table_headers(table: Tag) -> list[ResultSet[Tag]]:
    thead = table.find('thead')
    header_rows: list[ResultSet[Tag]] = []
    if isinstance(thead, Tag):
        raw_rows: ResultSet[Tag] = thead.find_all('tr')
        if len(raw_rows) == 0:
            raw_headers = thead.find_all('th')
            if len(raw_headers) != 0:
                header_rows.append(raw_headers)
        else:
            for raw_row in raw_rows:
                raw_headers = raw_row.find_all('th')
                if len(raw_headers) != 0:
                    header_rows.append(raw_headers)
    elif thead is None:
        raw_rows: ResultSet[Tag] = table.find_all('tr')
        if len(raw_rows) == 0:
            raw_headers = table.find_all('th')
            if len(raw_headers) != 0:
                header_rows.append(raw_headers)
        else:
            for raw_row in raw_rows:
                raw_headers = raw_row.find_all('th')
                if len(raw_headers) != 0:
                    header_rows.append(raw_headers)
    else:
        raise SummaryGenError('missing table headers')
    return header_rows


def get_table_body(table: Tag) -> list[ResultSet[Tag]]:
    tbody = table.find('tbody')
    if not isinstance(tbody, Tag):
        raise SummaryGenError('missing table body')
    raw_rows: ResultSet[Tag] = tbody.find_all('tr')
    body_rows: list[ResultSet[Tag]] = []
    for raw_row in raw_rows:
        raw_cells: ResultSet[Tag] = raw_row.find_all('td')
        if len(raw_cells) > 0:
            body_rows.append(raw_cells)
    return body_rows


def get_spans(table_content: list[list[Tag | None]]) -> list[_TABLE_SPAN]:
    span_list: list[_TABLE_SPAN] = []
    for i, row in enumerate(table_content):
        for j, col in enumerate(row):
            if col is None:
                continue
            spans = (int(col.get('rowspan', 0)), int(col.get('colspan', 0)))
            if sum(spans) != 0:
                span_list.append(((i, j), spans))
    return span_list


def gen_spanned_table(rows: list[ResultSet[Tag]]) -> list[list[ElementLine]]:
    content = copy.deepcopy(rows)
    for i, row in enumerate(rows):
        x_offset = 0
        for j, cell in enumerate(row):
            x = j + x_offset
            row_span = int(cell.get('colspan', 0))
            for _ in range(row_span - 1):
                content[i].insert(x + 1, None)
                x_offset += 1

            col_span = int(cell.get('rowspan', 0))
            for k in range(i + 1, i + col_span):
                try:
                    content[k]
                    row_len = len(content[k])
                    if row_len < x + 1:
                        content[k].extend([None] * ((x + 1) - row_len))
                    else:
                        content[k].insert(x, None)
                except IndexError:
                    break
    return content


def convert_spanned_table(content: list[ResultSet[Tag]],
                          headers: int=1
                         ) -> list[list[ElementLine]]:
    table_body: list[list[ElementLine]] = []
    for i, row in enumerate(content):
        table_row: list[ElementLine] = []
        if i < headers:
            style = PSTYLES['ValueTableHeaderThin']
        else:
            style = PSTYLES['ValueTableDeterminant']
        for cell in row:
            if cell is None:
                element = ElementLine([ParagraphElement('')], style=style)
            else:
                cell_elements = _parse_element(cell)
                element = ElementLine(elements=cell_elements,
                                      max_width=None,
                                      style=style)
            table_row.append(element)
        table_body.append(table_row)
    return table_body


def split_word(element: ParagraphElement,
               rem_width: float=INNER_WIDTH,
               max_width: float=INNER_WIDTH
              ) -> list[ParagraphElement]:
    width = rem_width
    word: str = element.text
    frags: list[ParagraphElement] = []
    i = 0
    while i < len(word):
        j = i + 1
        elem_frag = element.copy(text=word[i:j])
        while j < len(word) and elem_frag.width < width:
            j += 1
            elem_frag = element.copy(text=word[i:j])

        if j == len(word):
            frags.append(elem_frag)
            break

        frags.append(element.copy(text=word[i:j - 1]))
        i = j - 1
        width = max_width
    return frags


def wrap_elements(elements: list[ParagraphElement],
                  max_width: float=INNER_WIDTH,
                  style: BetterParagraphStyle | None=None
                 ) -> list[ElementLine]:
    element_lines: list[ElementLine] = []
    current_line = ElementLine(max_width=max_width, style=style)
    for element in elements:
        try:
            current_line.add(element)
        except WidthExceededError:
            for elem in element.split():
                try:
                    current_line.add(elem)
                except WidthExceededError:
                    if elem.width > max_width:
                        avail_width = max_width - current_line.width
                        word_frags = split_word(elem, avail_width, max_width)
                        current_line.add(word_frags[0])
                        element_lines.append(current_line)
                        if len(word_frags) > 1:
                            for word_frag in word_frags[1:len(word_frags)]:
                                current_line = ElementLine(max_width=max_width,
                                                           style=style)
                                current_line.add(word_frag)
                        else:
                            current_line = ElementLine(max_width=max_width,
                                                       style=style)
                    else:
                        element_lines.append(current_line)
                        current_line = ElementLine(max_width=max_width,
                                                   style=style)
                        current_line.add(elem)
    if len(current_line) != 0:
        element_lines.append(current_line)
    return element_lines


def gen_image(_url: str, max_width=INNER_WIDTH) -> Image:
    img_name = _url[_url.rindex('/') + 1:]
    response = requests.get(_url, stream=True)
    if response.status_code != 200:
        return []
    tmp_dir = os.path.join(_ROOT, 'assets', 'images', 'tmp')
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
    tmp_path = f'{tmp_dir}/{img_name}'
    with open(tmp_path, 'wb+') as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response
    img = Image(tmp_path)
    img_width = img.imageWidth
    img_height = img.imageHeight
    if img.imageWidth > max_width:
        aspect = img_height / float(img_width)
        del img
        img = Image(tmp_path, width=max_width, height=max_width * aspect)
    return img


def calc_col_widths(data: list[list[ElementLine]],
                    style: BetterTableStyle,
                    spans: list[_TABLE_SPAN]=[]
                   ) -> list[float]:
    span_dict = {str((y, x)): col_span for (y, x), (_, col_span) in spans}
    headers = data[0]
    base_width = INNER_WIDTH / len(headers)
    width_matrix: list[list[float]] = []
    skip = 0
    for y, row in enumerate(data):
        matrix_row: list[float] = []
        for x in range(len(row)):
            if skip != 0:
                skip -= 1
                continue
            frags = wrap_elements(row[x].elements, max_width=base_width)
            if frags == []:
                width = 0
            else:
                width = max([line.width for line in frags])
            col_span = span_dict.get(str((y, x)), 0)
            if col_span > 1:
                width_frags = [width / col_span] * col_span
                width_frags[0] += style.left_padding
                width_frags[-1] += style.right_padding
                matrix_row.extend(width_frags)
                skip = col_span - 1
            else:
                width += style.left_padding + style.right_padding
                matrix_row.append(width)
        width_matrix.append(matrix_row)

    for (y, x), (row_span, _) in spans:
        if row_span > 1:
            width = max([widths for widths in zip(*width_matrix)][x])
            for i in range(y, y + row_span):
                width_matrix[i][x] = width

    return [max(widths) for widths in zip(*width_matrix)]


def calc_row_heights(data: list[list[ElementLine]],
                     col_widths: list[float],
                     style: BetterTableStyle,
                     spans: list[_TABLE_SPAN]=[]
                    ) -> list[float]:
    span_dict = {str((y, x)): span_sizes for (y, x), span_sizes in spans}
    height_matrix: list[list[float]] = []
    skip = 0
    for y, row in enumerate(data):
        matrix_row: list[float] = []
        for x in range(len(row)):
            if skip != 0:
                skip -= 1
                continue
            row_span, col_span = span_dict.get(str((y, x)), (0, 0))
            if col_span > 1:
                col_width = sum(col_widths[x:x + col_span - 1])
            else:
                col_width = col_widths[x]
            frags = wrap_elements(row[x].elements, col_width)
            height = row[x].height * len(frags)
            if col_span > 1:
                height_frags = [height] * col_span
                height_frags[0] += style.top_padding
                height_frags[-1] += style.bottom_padding
                matrix_row.extend(height_frags)
                skip = col_span - 1
            else:
                height += style.top_padding + style.bottom_padding
                matrix_row.append(height)
        height_matrix.append(matrix_row)

    for (y, x), (row_span, _) in spans:
        if row_span > 1:
            col = [heights for heights in zip(*height_matrix)][x]
            height_frag = max(col) / row_span
            for i in range(y, y + row_span):
                height_matrix[i][x] = height_frag

    return [max(heights) for heights in height_matrix]


class CharacterizationParser:
    def __init__(self,
                 measure: Measure,
                 connection: ETRMConnection,
                 name: str):
        self.measure = measure
        self.connection = connection
        self.html = measure.characterizations[name]
        self.flowables = FlowableList()
        self.width, self.height = PAGESIZE

    def gen_summary_paragraph(self,
                              elements: list[ParagraphElement]
                             ) -> Table | None:
        lines = [[ParagraphLine(line, self.measure)]
                    for line
                    in wrap_elements(elements)]
        if lines == []:
            return None

        col_widths = [INNER_WIDTH]
        row_heights = [DEF_PSTYLE.leading] * len(lines)
        return Table(lines,
                     colWidths=col_widths,
                     rowHeights=row_heights,
                     style=TSTYLES['ElementLine'],
                     hAlign='LEFT')

    def __gen_table(self,
                    data: list[list[ElementLine]],
                    style: BetterTableStyle,
                    spans: list[_TABLE_SPAN]=[]
                   ) -> Table:
        span_dict = {str((y, x)): span_sizes for (y, x), span_sizes in spans}

        # calculate table cell widths/heights
        col_widths = calc_col_widths(data, style, spans=spans)
        # TODO: remove padding removal for items in the middle of a span
        h_padding = style.left_padding + style.right_padding
        cell_widths = [math.ceil(width - h_padding) for width in col_widths]
        row_heights = calc_row_heights(data, col_widths, style, spans=spans)

        # wrap data to fit calculated sizes
        frags: list[list[list[ElementLine]]] = []
        for y, table_row in enumerate(data):
            frag_line: list[list[ElementLine]] = []
            for x, elem_line in enumerate(table_row):
                _, col_span = span_dict.get(str((y, x)), (0, 0))
                if col_span > 1:
                    cell_width = sum(cell_widths[x:x + col_span - 1])
                else:
                    cell_width = cell_widths[x]
                frag_line.append(wrap_elements(elem_line.elements,
                                               max_width=cell_width))
            frags.append(frag_line)

        # convert wrapped data into flowables
        table_cells: list[list[TableCell | str]] = []
        for y, frag_line in enumerate(frags):
            cells: list[TableCell] = []
            for x, table_cell in enumerate(frag_line):
                if table_cell == []:
                    cell = ''
                else:
                    cell_lines: list[ParagraphLine] = []
                    for element_line in table_cell:
                        para_line = ParagraphLine(element_line=element_line,
                                                  measure=self.measure)
                        cell_lines.append(para_line)
                    _, col_span = span_dict.get(str((y, x)), (0, 0))
                    if col_span > 1:
                        col_width = sum(col_widths[x:x + col_span - 1])
                    else:
                        col_width = col_widths[x]
                    cell = TableCell(cell_lines, width=col_width)
                cells.append(cell)
            table_cells.append(cells)

        return Table(table_cells,
                     colWidths=col_widths,
                     rowHeights=row_heights,
                     style=style,
                     hAlign='LEFT')

    def get_table_content(self, table: ValueTable) -> list[list[ElementLine]]:
        headers: list[ElementLine] = []
        for api_name in table.determinants:
            determinant = self.measure.get_determinant(api_name)
            element_line = ElementLine(max_width=None,
                                       style=PSTYLES['ValueTableHeader'])
            element = ParagraphElement(text=determinant.name)
            element_line.add(element)
            headers.append(element_line)
        for column in table.columns:
            element_line = ElementLine(max_width=None)
            text = f'{column.name} ({column.unit})'
            text_element = ParagraphElement(text=text,
                                            style=PSTYLES['ValueTableHeader'])
            element_line.add(text_element)
            for ref in column.reference_refs:
                ref_element = ParagraphElement(text=ref, type=ElemType.REF)
                element_line.add(ref_element)
            headers.append(element_line)

        body: list[list[ElementLine]] = []
        for row in table.values:
            table_row: list[ElementLine] = []
            for i, item in enumerate(row):
                if i < len(table.determinants):
                    style = PSTYLES['ValueTableDeterminant']
                else:
                    style = PSTYLES['ValueTableItem']
                if item is None:
                    text = ''
                else:
                    text = item
                element = ParagraphElement(text)
                table_row.append(ElementLine(elements=[element], style=style))
            body.append(table_row)

        data = [headers]
        data.extend(body)
        return data

    def gen_embedded_value_table(self, table: ValueTable) -> Table | None:
        data = self.get_table_content(table)
        if data == None:
            return None
        style = get_table_style(data, determinants=len(table.determinants))
        return self.__gen_table(data, style)

    def gen_static_value_table(self, element: Tag) -> Table | None:
        headers = get_table_headers(element)
        body = get_table_body(element)
        data = [*headers, *body]
        spanned_table = gen_spanned_table(data)
        spans = get_spans(spanned_table)
        content = convert_spanned_table(spanned_table, headers=len(headers))
        style = get_table_style(content,
                                determinants=len(content),
                                headers=len(headers),
                                spans=spans)
        return self.__gen_table(content, style, spans=spans)

    def _parse_list(self, ul: Tag) -> list[ListItem]:
        list_items: list[ListItem] = []
        li_list: ResultSet[Tag] = ul.find_all('li')
        for li in li_list:
            items = _parse_element(li)
            element = self.gen_summary_paragraph(items)
            if element != None:
                list_item = ListItem(element, bulletColor=colors.black)
                list_items.append(list_item)
        return list_items

    def _parse_text(self, text: str) -> Flowable:
        if text == '\n':
            return KeepTogether(Spacer(letter[0], 9.2))
        return Paragraph(text, PSTYLES['Paragraph'])

    def _parse_embedded_tag(self, tag: Tag) -> Flowable | None:
        json_str = tag.attrs.get('data-etrmreference', None)
        if json_str != None:
            ref_tag = ReferenceTag(json_str)
            ref_link = f'{self.measure.link}/#references_list'
            return Reference(ref_tag.text, ref_link)

        json_str = tag.attrs.get('data-etrmvaluetable', None)
        if json_str != None:
            vt_tag = EmbeddedValueTableTag(json_str)
            if vt_tag.obj_deleted:
                return None

            change_id = vt_tag.obj_info.change_url.split('/')[4]
            table_link = f'{self.measure.link}/value-table/{change_id}/'
            value_table: ValueTable | None = None
            possible_names = [vt_tag.obj_info.api_name_unique,
                              vt_tag.obj_info.title,
                              vt_tag.obj_info.verbose_name]
            for name in possible_names:
                value_table = self.measure.get_value_table(name)
                if value_table != None:
                    break
            if value_table == None:
                table_name = vt_tag.obj_info.verbose_name
                raise SummaryGenError(f'value table {table_name} does not exist'
                                      f' in {self.measure.full_version_id}')
            header = ValueTableHeader(value_table.name, table_link)
            table = self.gen_embedded_value_table(table=value_table)
            if table == None:
                return None

            return KeepTogether([header, table])

        json_str = tag.attrs.get('data-ombuimage', None)
        if json_str != None:
            img_tag = EmbeddedImage(json_str)
            img_url = img_tag.obj_info.image_url
            _url = f'{ETRM_URL}{img_url}'
            return gen_image(_url)
        return None

    def gen_header(self, header: Tag) -> Flowable:
        if len(header.contents) < 1:
            return Paragraph('', PSTYLES[header.name])

        elements = _parse_element(header.contents[0])
        text = ''
        for element in elements:
            text += element.text_xml
        return XPreformatted(text, PSTYLES[header.name])

    def _parse_element(self, element: PageElement) -> list[Flowable]:
        if isinstance(element, NavigableString):
            return [self._parse_text(element.get_text())]

        if not isinstance(element, Tag):
            return []

        if is_embedded(element):
            flowable = self._parse_embedded_tag(element)
            if flowable == None:
                return []
            return [flowable]

        match element.name:
            case 'div' | 'span':
                flowables: list[Flowable] = []
                for child in element.contents:
                    flowables.extend(self._parse_element(child))
                return flowables
            case 'a':
                _url = element.get('href', None)
                if _url != None:
                    img = gen_image(_url)
                    flowables: list[Flowable] = []
                    if self.flowables.can_fit(KeepTogether([NEWLINE, img])):
                        flowables.append(KeepTogether([NEWLINE, img]))
                    elif self.flowables.can_fit(img):
                        flowables.extend([NEWLINE, img])
                    return flowables
                return []
            case 'p':
                elements: list[ParagraphElement] = []
                for child in element.contents:
                    elements.extend(_parse_element(child))
                para = self.gen_summary_paragraph(elements)
                if para is None:
                    return []
                return [para]
            case 'h3' | 'h6':
                return [self.gen_header(element)]
            case 'table':
                table = self.gen_static_value_table(element)
                if table is None:
                    return []
                return [table]
            case 'ul':
                elements = self._parse_list(element)
                return [ListFlowable(elements, bulletType='bullet')]
            case '<br>':
                return [NEWLINE]
            case tag:
                raise Exception(f'unsupported HTML tag: {tag}')

    def parse(self) -> list[Flowable]:
        self.flowables.clear()
        soup = BeautifulSoup(self.html, 'html.parser')
        top_level: ResultSet[PageElement] = soup.find_all(recursive=False)
        i = 0
        while i < len(top_level):
            element = top_level[i]
            parsed_elements = self._parse_element(element)
            if is_header(element):
                parsed_elements.append(Spacer(letter[0], 5))
                next_elements = self._parse_element(top_level[i + 1])
                extra_elements: list[Flowable] = []
                if len(next_elements) > 1:
                    parsed_elements.append(next_elements.pop(0))
                    extra_elements = next_elements
                else:
                    parsed_elements.extend(next_elements)
                parsed_elements = [KeepTogether(parsed_elements)]
                parsed_elements.extend(extra_elements)
                i += 1
            self.flowables.add(*parsed_elements)
            if (isinstance(element, Tag)
                    and (element.name != 'a')
                    and element.next_sibling == '\n'):
                self.flowables.add(NEWLINE)
            i += 1
        return self.flowables.flowables
