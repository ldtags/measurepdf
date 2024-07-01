from __future__ import annotations
import requests
import shutil
import os
import copy
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
from src.etrm.models import Measure
from src.exceptions import (
    SummaryGenError
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
    PSTYLES,
    DEF_PSTYLE,
    TSTYLES,
    INNER_WIDTH,
    INNER_HEIGHT,
    PAGESIZE
)
from src.summarygen.flowables import (
    Reference,
    ElementLine,
    ValueTable as ValueTableFlowable,
    EmbeddedValueTable,
    SummaryParagraph,
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


def get_image(_url: str, max_width=INNER_WIDTH) -> Image:
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

    def handle_text(self, element: NavigableString) -> Flowable:
        text = element.get_text()
        if text == '\n':
            return KeepTogether(Spacer(letter[0], 9.2))
        return Paragraph(text, PSTYLES['Paragraph'])

    def handle_embedded_tag(self, tag: Tag) -> Flowable | None:
        json_str = tag.attrs.get('data-etrmreference', None)
        if json_str != None:
            ref_tag = ReferenceTag(json_str)
            if ref_tag.obj_deleted:
                return None
            ref_link = f'{self.measure.link}/#references_list'
            return Reference(ref_tag.text, ref_link)

        json_str = tag.attrs.get('data-etrmvaluetable', None)
        if json_str != None:
            vt_tag = EmbeddedValueTableTag(json_str)
            if vt_tag.obj_deleted:
                return None
            return EmbeddedValueTable(table_info=vt_tag.obj_info,
                                      measure=self.measure)

        json_str = tag.attrs.get('data-ombuimage', None)
        if json_str != None:
            img_tag = EmbeddedImage(json_str)
            img_url = img_tag.obj_info.image_url
            _url = f'{ETRM_URL}{img_url}'
            return get_image(_url)
        return None

    def handle_h(self, header: Tag) -> Flowable:
        if len(header.contents) < 1:
            return Paragraph('', PSTYLES[header.name])

        elements = _parse_element(header.contents[0])
        text = ''
        for element in elements:
            text += element.text_xml
        return [XPreformatted(text, PSTYLES[header.name])]

    def handle_a(self, tag: Tag) -> list[Flowable]:
        _url = tag.get('href', None)
        if _url != None:
            img = get_image(_url)
            flowables: list[Flowable] = []
            if self.flowables.can_fit(KeepTogether([NEWLINE, img])):
                flowables.append(KeepTogether([NEWLINE, img]))
            elif self.flowables.can_fit(img):
                flowables.extend([NEWLINE, img])
            return flowables
        return []

    def handle_p(self, tag: Tag) -> list[Flowable]:
        elements: list[ParagraphElement] = []
        for child in tag.contents:
            elements.extend(_parse_element(child))
        if elements == []:
            return []
        return [SummaryParagraph(elements, self.measure)]

    def handle_table(self, tag: Tag) -> list[Flowable]:
        headers = get_table_headers(tag)
        body = get_table_body(tag)
        data = [*headers, *body]
        spanned_table = gen_spanned_table(data)
        spans = get_spans(spanned_table)
        content = convert_spanned_table(spanned_table, headers=len(headers))
        return [ValueTableFlowable(data=content,
                                   measure=self.measure,
                                   headers=len(headers),
                                   determinants=len(content),
                                   spans=spans)]

    def handle_ul(self, tag: Tag) -> list[Flowable]:
        list_items: list[ListItem] = []
        li_list: ResultSet[Tag] = tag.find_all('li')
        for li in li_list:
            items = _parse_element(li)
            element = SummaryParagraph(items, self.measure)
            if element != None:
                list_item = ListItem(element, bulletColor=colors.black)
                list_items.append(list_item)
        return [ListFlowable(list_items, bulletType='bullet')]

    def parse_contents(self, tag: Tag) -> list[Flowable]:
        flowables: list[Flowable] = []
        for element in tag.contents:
            flowables.extend(self.parse_element(element))
        return flowables

    def parse_element(self, element: PageElement) -> list[Flowable]:
        if isinstance(element, NavigableString):
            return self.handle_text()

        if not isinstance(element, Tag):
            return []

        if is_embedded(element):
            flowable = self.handle_embedded_tag(element)
            if flowable == None:
                return []
            return [flowable]

        match element.name:
            case 'div' | 'span':
                return self.parse_contents(element)
            case 'a':
                return self.handle_a(element)
            case 'p':
                return self.handle_p(element)
            case 'h3' | 'h6':
                return self.handle_h(element)
            case 'table':
                return self.handle_table(element)
            case 'ul':
                return self.handle_ul(element)
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
            parsed_elements = self.parse_element(element)
            if is_header(element):
                parsed_elements.append(Spacer(letter[0], 5))
                next_elements = self.parse_element(top_level[i + 1])
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
