from __future__ import annotations
import requests
import shutil
import os
import math
from bs4 import (
    BeautifulSoup,
    Tag,
    NavigableString,
    ResultSet,
    PageElement
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    ListFlowable,
    ListItem,
    Spacer,
    KeepTogether,
    Image
)

from src import _ROOT
from src.etrm import ETRM_URL
from src.etrm.models import Measure, ValueTable
from src.exceptions import (
    SummaryGenError,
    WidthExceededError
)
from src.summarygen.models import (
    ParagraphElement,
    ReferenceTag,
    EmbeddedValueTableTag,
    TextStyle,
    EmbeddedImage
)
from src.summarygen.styling import (
    BetterTableStyle,
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES,
    INNER_WIDTH,
    X_MARGIN,
    PAGESIZE,
    value_table_style
)
from src.summarygen.flowables import (
    TableCell,
    Reference,
    ValueTableHeader,
    ElementLine,
    ParagraphLine,
    NEWLINE
)


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
        case _:
            raise RuntimeError(f'unsupported tag: {element.name}')


def _parse_elements(elements: list[PageElement]) -> list[ParagraphElement]:
    contents: list[ParagraphElement] = []
    for element in elements:
        parsed_elements = _parse_element(element)
        if parsed_elements != None:
            contents.extend(parsed_elements)
    return contents


def parse_table_headers(table: Tag) -> list[TableCell]:
    thead = table.find('thead')
    raw_headers: ResultSet[Tag] = []
    if thead == None:
        raw_headers = table.find_all('th')
    elif isinstance(thead, Tag):
        raw_headers = thead.find_all('th')
    else:
        raise SummaryGenError('missing table headers')
    max_width = (letter[0] - 3.25 * inch) / len(raw_headers)
    headers: list[TableCell] = []
    for raw_header in raw_headers:
        header_elements = _parse_element(raw_header)
        headers.append(TableCell(header_elements,
                                 max_width,
                                 style=PSTYLES['ValueTableHeader']))
    return headers


def parse_table_body(table: Tag) -> list[list[TableCell]]:
    tbody = table.find('tbody')
    if not isinstance(tbody, Tag):
        raise SummaryGenError('missing table body')
    raw_rows: ResultSet[Tag] = tbody.find_all('tr')
    body_rows: list[list[TableCell]] = []
    for raw_row in raw_rows:
        raw_cells: ResultSet[Tag] = raw_row.find_all('td')
        max_width = (letter[0] - 3.25 * inch) / len(raw_cells)
        cells: list[TableCell] = []
        for raw_cell in raw_cells:
            cell_elements = _parse_element(raw_cell)
            cells.append(TableCell(cell_elements, max_width))
        body_rows.append(cells)
    return body_rows


def parse_table(table: Tag) -> list[list[TableCell]]:
    headers = parse_table_headers(table)
    body = parse_table_body(table)
    data: list[list[TableCell]] = []
    data.append(headers)
    data.extend(body)
    return data


def calc_col_width(element: TableCell | str,
                   style: BetterTableStyle
                  ) -> float:
    if isinstance(element, str):
        width = stringWidth(element, style.font_name, style.font_size)
    else:
        width = element.width
    padding = style.left_padding + style.right_padding
    return width + padding


def calc_col_widths(data: list[list[TableCell | str]],
                    style: BetterTableStyle
                   ) -> list[float]:
    headers = data[0]
    col_widths: list[float] = list(range(len(headers)))
    for i in range(len(headers)):
        max_width = 0
        for j in range(len(data)):
            col_width = calc_col_width(data[j][i], style)
            if col_width > max_width:
                max_width = col_width
        col_widths[i] = max_width
    return col_widths


def calc_row_height(element: TableCell | str,
                    style: BetterTableStyle
                   ) -> float:
    if isinstance(element, str):
        height = style.font_size
    else:
        height = element.height
    padding = style.top_padding + style.bottom_padding
    return height + padding


def calc_row_heights(data: list[list[TableCell | str]],
                     style: BetterTableStyle
                    ) -> list[float]:
    row_heights: list[float] = list(range(len(data)))
    for i in range(len(data)):
        max_height = 0
        for cell in data[i]:
            cell_height = calc_row_height(cell, style)
            if cell_height > max_height:
                max_height = cell_height
        row_heights[i] = max_height
    return row_heights


def split_word(element: ParagraphElement,
               avail_width: float=INNER_WIDTH
              ) -> list[ParagraphElement]:
    width = avail_width
    word: str = element.text
    fractions: list[ParagraphElement] = []
    while word != '':
        i = 0
        while i < len(word):
            if element.copy(word[0:i]).width > width:
                break
            i += 1
        fractions.append(element.copy(word[0:i]))
        word[0:i] = ''
        width = INNER_WIDTH
    return fractions


def split_element(element: ParagraphElement) -> list[ParagraphElement]:
    elements: list[ParagraphElement] = []
    words = element.text.split()
    word_count = len(words)
    if word_count == 0:
        return elements
    elif word_count == 1:
        elements.append(element)
        return elements

    if element.text == '':
        return elements

    if element.text[0] == ' ':
        words[0] = f' {words[0]}'

    if len(element.text) > 1 and element.text[-1] == ' ':
        words[-1] = f'{words[-1]} '

    if word_count == 2:
        elements.append(element.copy(f'{words[0]} '))
        elements.append(element.copy(words[1]))
    else:
        for i, word in enumerate(words):
            if i == 0:
                elem_cpy = element.copy(word)
            else:
                elem_cpy = element.copy(f' {word}')
            elements.append(elem_cpy)
    return list(filter(lambda e: e.text != '', elements))


def wrap_elements(elements: list[ParagraphElement],
                  max_width: float=INNER_WIDTH
                 ) -> list[ElementLine]:
    element_lines: list[ElementLine] = []
    current_line = ElementLine(max_width=max_width)
    for element in elements:
        try:
            current_line.add(element)
        except WidthExceededError:
            split_elems = split_element(element)
            for elem in split_elems:
                try:
                    current_line.add(elem)
                except WidthExceededError:
                    if elem.width > max_width:
                        avail_width = max_width - current_line.width
                        word_frags = split_word(elem.width, avail_width)
                        current_line.add(word_frags[0])
                        element_lines.append(current_line)
                        if len(word_frags) > 1:
                            for word_frag in word_frags[1:len(word_frags) - 1]:
                                current_line = ElementLine(max_width=max_width)
                                current_line.add(word_frag)
                        else:
                            current_line = ElementLine(max_width=max_width)
                    else:
                        element_lines.append(current_line)
                        current_line = ElementLine(max_width=max_width)
                        current_line.add(elem)
    if len(current_line) != 0:
        element_lines.append(current_line)
    return element_lines


def gen_image(_url: str) -> Image:
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
    return img


class CharacterizationParser:
    def __init__(self,
                 measure: Measure,
                 name: str):
        self.measure = measure
        self.html = measure.characterizations[name]
        self.flowables: list[Flowable] = []
        self.width, self.height = PAGESIZE
        self.inner_width = self.width - X_MARGIN * 2

    def gen_summary_paragraph(self,
                              elements: list[PageElement]
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

    def gen_embedded_value_table(self,
                                 vt_tag: EmbeddedValueTableTag,
                                 table: ValueTable
                                ) -> Table | None:
        column_indexes: list[int] = []
        headers: list[str] = []
        for i, column in enumerate(table.columns):
            if column.api_name in vt_tag.obj_info.vtconf.cids:
                column_indexes.append(i)
                headers.append(column.name)
        body: list[list[str]] = []
        for value_row in table.values:
            row: list[str] = []
            for index in column_indexes:
                row.append(value_row[index])
            body.append(row)
        data = [headers]
        data.extend(body)
        if data == [[]]:
            return None

        style = value_table_style(data, embedded=True)
        col_widths = calc_col_widths(data, style)
        row_heights = calc_row_heights(data, col_widths, style)
        return Table(data,
                     colWidths=col_widths,
                     rowHeights=row_heights,
                     style=style,
                     hAlign='LEFT')

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
            return Spacer(letter[0], 9.2)
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
            change_id = vt_tag.obj_info.change_url.split('/')[4]
            table_link = f'{self.measure.link}/value-table/{change_id}/'
            api_name = vt_tag.obj_info.api_name_unique
            table_obj = self.measure.get_value_table(api_name)
            if table_obj == None:
                raise SummaryGenError(f'value table {api_name} does not exist'
                                      f' in {self.measure.full_version_id}')
            header = ValueTableHeader(table_obj.name, table_link)
            table = self.gen_embedded_value_table(vt_tag, table_obj)
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

    def _parse_header(self, header: Tag) -> Paragraph:
        if len(header.contents) != 1:
            raise Exception('temp exception')

        child = header.contents[0]
        if not isinstance(child, NavigableString):
            raise Exception('temp exception')

        return Paragraph(child.get_text(), PSTYLES[header.name])

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
                    return [KeepTogether([NEWLINE,
                                          gen_image(_url),
                                          NEWLINE])]
                return []
            case 'p':
                elements: list[ParagraphElement] = []
                for child in element.contents:
                    elements.extend(_parse_element(child))
                para = self.gen_summary_paragraph(elements)
                if para == None:
                    return []
                return [para]
            case 'h3' | 'h6':
                return [self._parse_header(element)]
            case 'table':
                data = parse_table(element)
                style = value_table_style(data, embedded=True)
                col_widths = calc_col_widths(data, style)
                row_heights = calc_row_heights(data, style)
                if data == [[]]:
                    return []
                table = Table(data=data,
                              colWidths=col_widths,
                              rowHeights=row_heights,
                              style=style,
                              hAlign='LEFT')
                return [table]
            case 'ul':
                elements = self._parse_list(element)
                return [ListFlowable(elements, bulletType='bullet')]
            case tag:
                raise Exception(f'unsupported HTML tag: {tag}')

    def parse(self) -> list[Flowable]:
        self.flowables = []
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
            self.flowables.extend(parsed_elements)
            if (isinstance(element, Tag)
                    and (element.name != 'a')
                    and element.next_sibling == '\n'):
                self.flowables.append(NEWLINE)
            i += 1
        return self.flowables
