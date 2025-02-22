from __future__ import annotations
import math
from enum import Enum
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    Spacer,
    Paragraph
)

from src.summarygen.styles import (
    INNER_WIDTH,
    INNER_HEIGHT,
    PSTYLES,
    DEF_PSTYLE,
    ParagraphStyle
)
from src.summarygen.exceptions import (
    WidthExceededError,
    ElementJoinError
)


class ElemType(Enum):
    TEXT = 'text'
    REF = 'ref'
    SPACE = 'space'
    NEWLINE = 'newline'


class TextStyle(Enum):
    NORMAL = 'normal'
    STRONG = 'strong'
    ITALIC = 'em'
    SUP = 'sup'
    SUB = 'sub'
    LINK = 'link'
    PRE = 'pre'


_TYPE_STYLES = {
    ElemType.TEXT: [TextStyle.NORMAL],
    ElemType.REF: [TextStyle.STRONG],
    ElemType.SPACE: [TextStyle.NORMAL],
    ElemType.NEWLINE: [TextStyle.NORMAL]
}


class ParagraphElement:
    """Defines an element found in an HTML document."""

    __DEFAULT_STYLES = [TextStyle.NORMAL]

    def __init__(
        self,
        text: str,
        type: ElemType = ElemType.TEXT,
        styles: list[TextStyle] | None = None,
        style: ParagraphStyle | None = None,
        href: str | None = None
    ) -> None:
        self.text = text.replace("\n", "")
        self.href = href
        self.type = type
        if styles is not None:
            self.styles = styles
        else:
            self.styles = [*_TYPE_STYLES.get(type, self.__DEFAULT_STYLES)]
            if self.href is not None:
                self.styles.append(TextStyle.LINK)

        self.__style = style

    @property
    def text_xml(self) -> str:
        text = self.text
        cur_styles: list[TextStyle] = []
        for style in self.styles:
            match style:
                case TextStyle.SUP:
                    if TextStyle.SUB not in cur_styles:
                        text = f'{text}'
                case TextStyle.SUB:
                    if TextStyle.SUP not in cur_styles:
                        text = f'{text}'
                case TextStyle.STRONG:
                    text = f'<b>{text}</b>'
                case TextStyle.ITALIC:
                    text = f'<i>{text}</i>'
                case TextStyle.LINK:
                    if self.href is not None:
                        text = f'<link href=\"{self.href}\">{text}</link>'
                case TextStyle.PRE:
                    text = f'<pre>{text}</pre>'
                case TextStyle.NORMAL:
                    pass
                case x:
                    raise ValueError(f'{x} is not a valid TextStyle')

            cur_styles.append(style)

        return text

    @property
    def style(self) -> ParagraphStyle:
        if self.__style is not None:
            return self.__style

        if self.type == ElemType.REF:
            return PSTYLES['ReferenceTag']

        if self.type == ElemType.SPACE:
            return PSTYLES['SmallParagraph']

        style = DEF_PSTYLE
        for text_style in self.styles:
            match text_style:
                case TextStyle.SUP:
                    style = style.superscripted
                case TextStyle.SUB:
                    style = style.subscripted
                case TextStyle.STRONG:
                    style = style.bold
                case TextStyle.ITALIC:
                    style = style.italic
                case TextStyle.LINK:
                    style = style.link
                case _:
                    pass

        return style

    @style.setter
    def style(self, _style: ParagraphStyle):
        self.__style = _style

    @property
    def font_size(self) -> float:
        return self.style.font_size

    @property
    def font_name(self) -> str:
        return self.style.font_name

    @property
    def width(self) -> float:
        if self.type == ElemType.NEWLINE:
            return INNER_WIDTH - 0.01

        _width = stringWidth(self.text, self.font_name, self.font_size)
        _width += self.style.x_padding
        return _width

    @property
    def height(self) -> float:
        return self.style.leading

    def is_styled(self) -> bool:
        """Returns `True` if this element has a custom styling, otherwise
        (if the element uses the default styling) returns `False`.
        """

        return self.__style is not None

    def split(self, size: int=1) -> list[ParagraphElement]:
        elements: list[ParagraphElement] = []
        words = self.text.split()
        word_count = len(words)
        if word_count == 0:
            return elements
        elif word_count == 1:
            elements.append(self)
            return elements

        if self.text == '':
            return elements

        if self.text[0] == ' ':
            words[0] = f' {words[0]}'

        if len(self.text) > 1 and self.text[-1] == ' ':
            words[-1] = f'{words[-1]} '

        if word_count == 2:
            elements.append(self.copy(f'{words[0]} '))
            elements.append(self.copy(words[1]))
        else:
            for i, word in enumerate(words):
                if i == 0:
                    elem_cpy = self.copy(word)
                else:
                    elem_cpy = self.copy(f' {word}')
                elements.append(elem_cpy)

        elem_frags = list(filter(lambda e: e.text != '', elements))
        if size == 1 or size >= len(elem_frags):
            return elem_frags

        split_elems: list[ParagraphElement] = []
        for i in range(0, len(elem_frags), size):
            rem_size = len(elem_frags) - i
            if rem_size == 1:
                split_elems.append(elem_frags[i])
                continue

            elem = elem_frags[i]
            if rem_size < size:
                frag_indice = -1
            else:
                frag_indice = i + size

            elem.join(*elem_frags[i + 1:i + frag_indice])
            split_elems.append(elem)

        return split_elems

    def join(self, *elements: ParagraphElement) -> None:
        for element in elements:
            if self.type == ElemType.REF:
                raise ElementJoinError("Cannot join reference tags")

            if element.type == ElemType.SPACE:
                self.text += " "
                continue

            if self.type != element.type:
                raise ElementJoinError("Cannot join elements with different types")

            if self.styles != element.styles:
                raise ElementJoinError("Cannot join elements with different styles")

            if self.href != element.href:
                raise ElementJoinError("Cannot join elements with different links")

            self.text += element.text

    def copy(
        self,
        text: str | None=None,
        type: ElemType | None=None,
        styles: list[TextStyle] | None=None,
        style: ParagraphStyle | None=None
    ) -> ParagraphElement:
        return ParagraphElement(
            text or self.text,
            type or self.type,
            styles or self.styles,
            style or self.style
        )


class ElementLine:
    def __init__(
        self,
        string: str | None = None,
        elements: list[ParagraphElement] | None = None,
        max_width: float | None = INNER_WIDTH,
        style: ParagraphStyle | None = None
    ) -> None:
        self.style = style
        self.max_width = max_width
        self._elements: list[ParagraphElement] = []
        self.__index: int = 0

        if string is not None:
            element = ParagraphElement(string, style=self.style)
            self.add(element)

        if elements is not None:
            for element in elements:
                self.add(element)

    @property
    def elements(self) -> list[ParagraphElement]:
        if len(self._elements) == 0:
            return self._elements

        elements: list[ParagraphElement] = []
        for i, element in enumerate(self._elements):
            elem_types = [elem.type for elem in self._elements[i:]]
            if all([elem_type == ElemType.SPACE for elem_type in elem_types]):
                break

            elements.append(element.copy())

        return elements

    @property
    def width(self) -> float:
        return math.fsum([elem.width for elem in self.elements])

    @property
    def height(self) -> float:
        if self.elements == []:
            return 0

        return max([elem.height for elem in self.elements])

    @property
    def text(self) -> str:
        if self.elements == []:
            return ""

        return "".join([elem.text for elem in self.elements])

    def __getitem__(self, i: int) -> ParagraphElement:
        return self.elements[i]

    def __len__(self) -> int:
        return len(self.elements)

    def __iter__(self) -> ElementLine:
        return self

    def __next__(self) -> ParagraphElement:
        try:
            result = self.elements[self.__index]
        except IndexError:
            self.__index = 0
            raise StopIteration
        self.__index += 1
        return result

    def __add(self, element: ParagraphElement):
        if self.max_width is not None and element.width + self.width > self.max_width:
            raise WidthExceededError(f"Max width of {self.max_width} exceeded")

        try:
            self._elements[-1].join(element)
        except (IndexError, ElementJoinError):
            self._elements.append(element)

    def add(self, element: ParagraphElement):
        if element.text == '':
            return

        if self.style is not None and element.type != ElemType.REF:
            element.style = self.style

        if self.elements == []:
            new_elem = element.copy(element.text.lstrip())
        else:
            new_elem = element

        if element.type == ElemType.REF:
            self.__add(ParagraphElement(' ', type=ElemType.SPACE))
            self.__add(new_elem)
            self.__add(ParagraphElement(' ', type=ElemType.SPACE))
        else:
            self.__add(new_elem)

    def get_min_width(self, size: int=1) -> float:
        split_elems: list[ParagraphElement] = []
        for elem in self.elements:
            split_elems.extend(elem.split(size))

        if split_elems == []:
            return self.width

        return max([elem.width for elem in split_elems])

    def pop(self, index: int=-1) -> ParagraphElement:
        return self._elements.pop(index)


class Story:
    def __init__(
        self,
        inner_height: float=INNER_HEIGHT,
        inner_width: float=INNER_WIDTH
    ) -> None:
        self.inner_height = inner_height
        self.inner_width = inner_width
        self.__contents: list[Flowable] = []

    @property
    def contents(self) -> list[Flowable]:
        _contents = self.__contents

        # trim any trailing space
        i = len(_contents) - 1
        while i > 0 and isinstance(_contents[i], Spacer):
            _contents.pop()
            i -= 1

        return _contents

    def get_height(self, flowable: Flowable) -> float:
        if isinstance(flowable, KeepTogether | ListFlowable):
            height = 0
            for item in flowable._content:
                height += self.get_height(item)
        elif isinstance(flowable, Paragraph):
            _, height = flowable.wrap(INNER_WIDTH, 0)
        else:
            _, height = flowable.wrap(0, 0)

        return height

    def add(self, *flowables: Flowable):
        for flowable in flowables:
            self.__contents.append(flowable)

    def clear(self):
        self.contents = []
        self.current_height = 0
