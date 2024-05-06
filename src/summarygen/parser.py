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

from src.etrm import ETRM_URL
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
    StaticValueTable,
    Reference,
    EmbeddedValueTable,
    ValueTableHeader,
    SummaryList
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
            table_link = f'{ETRM_URL}/measure/{id_path}/value-table/{change_id}/'
            header = ValueTableHeader(table_obj.name, table_link)
            table = EmbeddedValueTable(self.measure, vt_tag)
            return [header, table]

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
                _flowables: list[Flowable] = []
                for child in element.contents:
                    _flowables.extend(self._parse_element(child))
                return _flowables
            case 'p':
                return [SummaryParagraph(element=element)]
            case 'h3' | 'h6':
                return [self._parse_header(element)]
            case 'table':
                # return [StaticValueTable(element=element)]
                return [Table([['Table Placeholder']])]
            case 'ul':
                return [SummaryList(element=element)]
            case tag:
                raise Exception(f'unsupported HTML tag: {tag}')

    def parse(self) -> list[Flowable]:
        self.flowables = []
        soup = BeautifulSoup(self.html, 'html.parser')
        top_level: ResultSet[PageElement] = soup.find_all(recursive=False)
        for element in top_level:
            self.flowables.extend(self._parse_element(element))
            if element.next_sibling == '\n':
                self.flowables.append(Spacer(letter[0], 9.2))
        return self.flowables
