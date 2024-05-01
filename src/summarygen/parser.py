from bs4 import (
    BeautifulSoup,
    Tag,
    NavigableString,
    ResultSet,
    PageElement
)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Table,
    ListFlowable,
    ListItem,
    Spacer
)

from src.summarygen.styling import (
    PSTYLES,
    value_table_style
)
from src.summarygen.models import ReferenceTag
from src.summarygen.flowables import SummaryParagraph


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


def embedded_handler(tag: Tag) -> Flowable | str | None:
    json_str = tag.attrs.get('data-etrmreference', None)
    if json_str != None:
        ref_tag = ReferenceTag(json_str)
        ref_rml = f'<para> {ref_tag.obj_info.title.upper()} </para>'
        return ref_rml

    json_str = tag.attrs.get('data-etrmvaluetable', None)
    if json_str != None:
        pass

    return None


def text_handler(text: str) -> Paragraph:
    sanitized_text = text.replace('\n', '<br />')
    return Paragraph(sanitized_text, PSTYLES['Paragraph'])


def header_handler(header: Tag) -> Paragraph:
    if len(header.children) != 1:
        raise Exception('temp exception')

    child = header.children[0]
    if not isinstance(child, NavigableString):
        raise Exception('temp exception')

    return Paragraph(child.get_text(), PSTYLES[header.name])


def table_handler(table_element: Tag) -> Table:
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
        else:
            headers.append(header)

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

    table_content: list[list[Flowable]] = []
    table_content.append(headers)
    table_content.extend(rows)
    return Table(table_content, style=value_table_style(table_content))


def list_handler(ul: Tag) -> ListFlowable:
    list_items: list[ListItem] = []
    li_list: ResultSet[Tag] = ul.find_all('li')
    for li in li_list:
        item = parse_element(li)
        if item == None:
            list_items.append(ListItem(Paragraph('')))
        else:
            list_items.append(ListItem(item))
    
    blt_list = ListFlowable(list_items, bulletType=1, start='square')


def parse_element(element: PageElement) -> Flowable | list[Flowable] | str | None:
    if isinstance(element, NavigableString):
        return text_handler(element.get_text())

    if not isinstance(element, Tag):
        return None

    if is_embedded(element):
        return embedded_handler(element)

    if len(element.contents) == 0:
        return None

    match element.name:
        case 'div' | 'span':
            parsed_elements = parse_elements(element.contents)
            if len(parsed_elements) == 1:
                return parsed_elements[0]
            return parsed_elements
        case 'p':
            return SummaryParagraph(element=element)
        case 'h3' | 'h6':
            return header_handler(element)
        case 'table':
            return table_handler(element)
        case 'ul':
            return list_handler(element)
        case ('sup' | 'sub') as tag:
            return f'<{tag}>{parse_elements(element.contents)}</{tag}>'
        case 'strong':
            return f'<b>{parse_elements(element.contents)}</b>'
        case tag:
            raise Exception(f'unsupported HTML tag: {tag}')


def parse_elements(elements: list[PageElement]) -> list[Flowable | str]:
    flowables: list[Flowable] = []
    for element in elements:
        sections = parse_element(element)
        if isinstance(sections, list):
            flowables.extend(sections)
        elif isinstance(sections, Flowable):
            flowables.append(sections)
        elif isinstance(sections, str):
            flowables.append(sections)
    return flowables


def parse_characterization(html: str) -> list[Flowable]:
    soup = BeautifulSoup(html, 'html.parser')
    top_level: ResultSet[PageElement] = soup.find_all(recursive=False)
    flowables: list[Flowable] = []
    for element in top_level:
        sections = parse_element(element)
        if isinstance(sections, list):
            flowables.extend(sections)
        elif isinstance(sections, Flowable):
            flowables.append(sections)
        if element.next_sibling == '\n':
            flowables.append(Spacer(letter[0], 9.2))
    return flowables
            
