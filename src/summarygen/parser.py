from reportlab.platypus import Flowable, Paragraph, Table, ListFlowable, ListItem
from bs4 import (
    BeautifulSoup,
    Tag,
    NavigableString,
    ResultSet,
    PageElement
)

from src.summarygen.styling import (
    STYLES,
    value_table_style,
    embedded_table_style
)
from src.summarygen.models import ReferenceTag


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


def embedded_handler(tag: Tag) -> Flowable | None:
    json_str = tag.attrs.get('data-etrmreference', None)
    if json_str != None:
        ref_tag = ReferenceTag(json_str)
        return Paragraph(ref_tag.obj_info.title.upper(),
                         STYLES['ReferenceTag'])

    json_str = tag.attrs.get('data-etrmvaluetable', None)
    if json_str != None:
        pass

    return None


def text_handler(text: str) -> Paragraph:
    sanitized_text = text.replace('\\n', '\n')
    return Paragraph(sanitized_text, STYLES['Paragraph'])


def header_handler(header: Tag) -> Paragraph:
    if len(header.children) != 1:
        raise Exception('temp exception')

    child = header.children[0]
    if not isinstance(child, NavigableString):
        raise Exception('temp exception')

    return Paragraph(child.get_text(), STYLES[header.name])


def table_handler(table_element: Tag) -> Table:
    table_content: list[list[Flowable]] = []
    thead = table_element.find('thead')
    raw_headers: ResultSet[Tag]
    if thead == None:
        raw_headers = table_element.find_all('th')
    elif isinstance(thead, Tag):
        raw_headers = thead.find_all('th')
    else:
        raise Exception('missing table headers')

    headers: list[Flowable] = []
    for raw_header in raw_headers:
        header = parse_element(raw_header)
        if header == None:
            headers.append(Paragraph(''))
        elif isinstance(header, Flowable):
            headers.append(header)
        else:
            raise Exception('illegal table formatting')
    table_content.append(headers)

    tbody = table_element.find('tbody')
    if not isinstance(tbody, Tag):
        return Exception('missing table body')

    raw_rows: ResultSet[Tag] = tbody.find_all('tr')
    rows: list[list[Flowable]] = []
    for raw_row in raw_rows:
        raw_cells: ResultSet[Tag] = raw_row.find_all('td')
        row: list[Flowable] = []
        for raw_cell in raw_cells:
            cell = parse_element(raw_cell)
            if cell == None:
                row.append(Paragraph(''))
            elif isinstance(cell, Flowable):
                row.append(cell)
            else:
                raise Exception('illegal table formatting')
        rows.append(row)
    table_content.extend(rows)
    return Table(table_content, style=value_table_style(table_content))


def list_handler(ulist: Tag) -> list[Flowable]:
    pass


def parse_element(element: PageElement) -> Flowable | list[Flowable] | None:
    if isinstance(element, NavigableString):
        return text_handler(element.get_text())

    if not isinstance(element, Tag):
        return None

    if is_embedded(element):
        return embedded_handler(element)

    if len(element.children) == 0:
        return None

    match element.name:
        case 'p' | 'div' | 'span':
            flowables: list[Flowable] = []
            for child in element.children:
                flowable = parse_element(child)
                if isinstance(flowable, Flowable):
                    flowables.append(flowable)
                elif isinstance(flowable, list):
                    flowables.extend(flowable)
            return flowables
        case 'h3' | 'h6':
            return header_handler(element)
        case 'table':
            return table_handler(element)
        case 'ul':
            return list_handler(element)
        case tag:
            raise Exception(f'unsupported HTML tag: {tag}')


def parse_characterization(html: str) -> list[Flowable]:
    flowables: list[Flowable] = []
    soup = BeautifulSoup(html, 'html.parser')
    top_level = soup.find_all(recursive=False)
    for element in top_level:
        flowable = parse_element(element)
        if isinstance(flowable, Flowable):
            flowables.append(flowable)
        elif isinstance(flowable, list):
            flowables.extend(flowable)
    return flowables
