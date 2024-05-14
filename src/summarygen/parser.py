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
    KeepTogether
)

from src.etrm import ETRM_URL
from src.etrm.models import Measure, ValueTable
from src.exceptions import SummaryGenError
from src.summarygen.models import (
    ParagraphElement,
    ReferenceTag,
    EmbeddedValueTableTag,
    TextStyle
)
from src.summarygen.styling import (
    PSTYLES,
    value_table_style
)
from src.summarygen.rlobjects import (
    BetterTableStyle
)
from src.summarygen.flowables import (
    SummaryParagraph,
    ElementLine,
    Reference,
    EmbeddedValueTable,
    ValueTableHeader
)


DEF_PSTYLE = PSTYLES['Paragraph']


def is_embedded(tag: Tag) -> bool:
    if tag.attrs.get('data-etrmreference'):
        return True

    if tag.attrs.get('data-etrmvaluetable'):
        return True

    if tag.attrs.get('data-etrmcalculation'):
        return True

    if tag.attrs.get('data-ombuimage'):
        return True

    return False


def _parse_element(element: PageElement) -> list[ParagraphElement]:
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
                    item.styles.append(style)
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


def _parse_table_headers(table: Tag) -> list[ElementLine]:
    thead = table.find('thead')
    raw_headers: ResultSet[Tag] = []
    if thead == None:
        raw_headers = table.find_all('th')
    elif isinstance(thead, Tag):
        raw_headers = thead.find_all('th')
    else:
        raise SummaryGenError('missing table headers')
    max_width = (letter[0] - 3.25 * inch) / len(raw_headers)
    headers: list[ElementLine] = []
    for raw_header in raw_headers:
        header_elements = _parse_element(raw_header)
        headers.append(ElementLine(header_elements,
                                   max_width,
                                   style=PSTYLES['ValueTableHeader']))
    return headers


def _parse_table_body(table: Tag) -> list[list[ElementLine]]:
    tbody = table.find('tbody')
    if not isinstance(tbody, Tag):
        raise SummaryGenError('missing table body')
    raw_rows: ResultSet[Tag] = tbody.find_all('tr')
    body_rows: list[list[ElementLine]] = []
    for raw_row in raw_rows:
        raw_cells: ResultSet[Tag] = raw_row.find_all('td')
        max_width = (letter[0] - 3.25 * inch) / len(raw_cells)
        cells: list[ElementLine] = []
        for raw_cell in raw_cells:
            cell_elements = _parse_element(raw_cell)
            cells.append(ElementLine(cell_elements, max_width))
        body_rows.append(cells)
    return body_rows


def _parse_table(table: Tag) -> list[list[ElementLine]]:
    headers = _parse_table_headers(table)
    body = _parse_table_body(table)
    data: list[list[ElementLine]] = []
    data.append(headers)
    data.extend(body)
    return data


def _col_width(element: ElementLine | str,
               style: BetterTableStyle
              ) -> float:
    if isinstance(element, str):
        width = stringWidth(element, style.font_name, style.font_size)
    else:
        width = element.width
    padding = style.left_padding + style.right_padding
    return width + padding


def _col_widths(data: list[list[ElementLine | str]],
                style: BetterTableStyle
               ) -> list[float]:
    headers = data[0]
    col_widths: list[float] = list(range(len(headers)))
    for i in range(len(headers)):
        max_width = 0
        for j in range(len(data)):
            col_width = _col_width(data[j][i], style)
            if col_width > max_width:
                max_width = col_width
        col_widths[i] = max_width
    return col_widths


def _row_height(element: ElementLine | str,
                style: BetterTableStyle) -> float:
    if isinstance(element, str):
        height = style.font_size
    else:
        height = element.height
    padding = style.top_padding + style.bottom_padding
    return height + padding


def _row_heights(data: list[list[ElementLine | str]],
                 style: BetterTableStyle
                ) -> list[float]:
    row_heights: list[float] = list(range(len(data)))
    for i in range(len(data)):
        max_height = 0
        for cell in data[i]:
            cell_height = _row_height(cell, style)
            if cell_height > max_height:
                max_height = cell_height
        row_heights[i] = max_height
    return row_heights


def _parse_list(ul: Tag) -> list[ListItem]:
    list_items: list[ListItem] = []
    li_list: ResultSet[Tag] = ul.find_all('li')
    for li in li_list:
        items = _parse_element(li)
        element = SummaryParagraph(paragraph_elements=items)
        list_items.append(ListItem(element,
                                   bulletColor=colors.black,
                                   value='square'))
    return list_items


class CharacterizationParser:
    def __init__(self, measure: Measure, name: str):
        self.measure = measure
        self.html = measure.characterizations[name]
        self.flowables: list[Flowable] = []

    def gen_embedded_value_table(self,
                                 vt_tag: EmbeddedValueTableTag,
                                 table: ValueTable
                                ) -> Table:
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
        style = value_table_style(data, embedded=True)
        return Table(data,
                     colWidths=_col_widths(data, style),
                     rowHeights=_row_heights(data, style),
                     style=style,
                     hAlign='LEFT')

    def _parse_text(self, text: str) -> Flowable:
        if text == '\n':
            return Spacer(letter[0], 9.2)
        return Paragraph(text, PSTYLES['Paragraph'])

    def _parse_embedded_tag(self, tag: Tag) -> list[Flowable]:
        json_str = tag.attrs.get('data-etrmreference', None)
        if json_str != None:
            ref_tag = ReferenceTag(json_str)
            return [Reference(self.measure, ref_tag)]

        json_str = tag.attrs.get('data-etrmvaluetable', None)
        if json_str != None:
            vt_tag = EmbeddedValueTableTag(json_str)
            id_path = '/'.join(self.measure.full_version_id.split('-'))
            change_id = vt_tag.obj_info.change_url.split('/')[4]
            table_link = f'{ETRM_URL}/measure/{id_path}/value-table/{change_id}/'
            api_name = vt_tag.obj_info.api_name_unique
            table_obj = self.measure.get_value_table(api_name)
            if table_obj == None:
                raise SummaryGenError(f'value table {api_name} does not exist'
                                      f' in {self.measure.full_version_id}')
            header = ValueTableHeader(table_obj.name, table_link)
            table = self.gen_embedded_value_table(vt_tag, table_obj)
            headed_table = KeepTogether([header, table])
            return [headed_table]

        return []

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
            return self._parse_embedded_tag(element)

        if len(element.contents) == 0:
            return []

        match element.name:
            case 'div' | 'span':
                flowables: list[Flowable] = []
                for child in element.contents:
                    flowables.extend(self._parse_element(child))
                return flowables
            case 'p':
                elements: list[ParagraphElement] = []
                for child in element.contents:
                    elements.extend(_parse_element(child))
                return [SummaryParagraph(paragraph_elements=elements)]
            case 'h3' | 'h6':
                return [self._parse_header(element)]
            case 'table':
                data = _parse_table(element)
                style = value_table_style(data, embedded=True)
                table = Table(data,
                              colWidths=_col_widths(data, style),
                              rowHeights=_row_heights(data, style),
                              style=style,
                              hAlign='LEFT')
                return [KeepTogether(table)]
            case 'ul':
                elements = _parse_list(element)
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
            if (isinstance(element, Tag)
                    and element.name in ['h3', 'h6']
                    and i < len(top_level) - 1):
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
            if element.next_sibling == '\n':
                self.flowables.append(Spacer(letter[0], 9.2))
            i += 1
        return self.flowables
