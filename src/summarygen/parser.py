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

from src.etrm import API_URL
from src.etrm.models import Measure
from src.summarygen.models import (
    ParagraphElement,
    ReferenceTag,
    EmbeddedValueTableTag
)
from src.summarygen.styling import (
    PSTYLES,
    value_table_style
)
from src.summarygen.flowables import (
    SummaryParagraph,
    Reference,
    EmbeddedValueTable,
    ValueTableHeader
)


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


class CharacterizationParser:
    def __init__(self, measure: Measure, name: str):
        self.measure = measure
        self.html = measure.characterizations[name]
        self.flowables: list[Flowable] = []

    def _parse_text(self, text: str) -> Paragraph:
        return Paragraph(text, PSTYLES['Paragraph'])

    def _parse_embedded_tag(self, tag: Tag) -> list[Flowable]:
        json_str = tag.attrs.get('data-etrmreference', None)
        if json_str != None:
            ref_tag = ReferenceTag(json_str)
            return [Reference(self.measure, ref_tag)]

        json_str = tag.attrs.get('data-etrmvaluetable', None)
        if json_str != None:
            vt_tag = EmbeddedValueTableTag(json_str)
            api_name = vt_tag.obj_info.api_name_unique
            table_obj = self.measure.get_value_table(api_name)
            id_path = '/'.join(self.measure.full_version_id.split('-'))
            change_id = vt_tag.obj_info.change_url.split('/')[4]
            table_link = f'{API_URL}/{id_path}/value-table/{change_id}/'
            header = ValueTableHeader(table_obj.name, table_link)
            table = EmbeddedValueTable(self.measure, vt_tag)
            return [header, table]

        return []

    def _parse_header(self, header: Tag) -> Paragraph:
        if len(header.children) != 1:
            raise Exception('temp exception')

        child = header.children[0]
        if not isinstance(child, NavigableString):
            raise Exception('temp exception')

        return Paragraph(child.get_text(), PSTYLES[header.name])

    def _parse_table(self, table_element: Tag) -> Table:
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
            header = self._parse_element(raw_header)
            if len(header) > 0:
                headers.append(header[0])
            else:
                headers.append(Paragraph(''))

        tbody = table_element.find('tbody')
        if not isinstance(tbody, Tag):
            return Exception('missing table body')

        raw_rows: ResultSet[Tag] = tbody.find_all('tr')
        rows: list[list[Flowable]] = []
        for raw_row in raw_rows:
            raw_cells: ResultSet[Tag] = raw_row.find_all('td')
            row: list[Flowable] = []
            for raw_cell in raw_cells:
                cells = self._parse_element(raw_cell)
                if len(cells) > 0:
                    row.append(cells[0])
                else:
                    row.append(Paragraph(''))
            rows.append(row)

        table_content: list[list[Flowable]] = []
        table_content.append(headers)
        table_content.extend(rows)
        return Table(table_content, style=value_table_style(table_content))

    def _parse_list(self, ul: Tag) -> ListFlowable:
        list_items: list[ListItem] = []
        li_list: ResultSet[Tag] = ul.find_all('li')
        for li in li_list:
            items = self._parse_element(li)
            for item in items:
                list_items.append(ListItem(item))

        return ListFlowable(list_items, bulletType=1, start='square')

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
                return list(
                    map(lambda child: self._parse_element(child),
                        element.contents))
            case 'p':
                return [SummaryParagraph(element=element)]
            case 'h3' | 'h6':
                return [self._parse_header(element)]
            case 'table':
                return [self._parse_table(element)]
            case 'ul':
                return [self._parse_list(element)]
            case tag:
                raise Exception(f'unsupported HTML tag: {tag}')

    def parse(self) -> list[Flowable]:
        self.flowables = []
        soup = BeautifulSoup(self.html, 'html.parser')
        top_level: ResultSet[PageElement] = soup.find_all(recursive=False)
        for element in top_level:
            self.flowables.extend(self._parse_element(element))
        return self.flowables
