from __future__ import annotations
import math
from reportlab.pdfbase.pdfmetrics import stringWidth

from src.summarygen.models.enums import ElementType, TextStyle
from src.summarygen.styles import (
    ParagraphStyle,
    DEF_PSTYLE,
    PSTYLES,
    INNER_WIDTH
)
from src.summarygen.exceptions import ElementJoinError, WidthExceededError


def escape(text: str) -> str:
    return (
        text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
            .replace("\'", "&#39;")
    )


class ParagraphElement:
    """Defines an element of a paragraph defined by the HTML.

    This class allows for styling multiple sections of a paragraph with
    different styles.
    """

    def __init__(
        self,
        text: str = "",
        type: ElementType = ElementType.Text,
        text_styles: list[TextStyle] | None = None,
        style: ParagraphStyle = DEF_PSTYLE,
        link: str | None = None
    ) -> None:
        self.type = type
        self.link = link
        self.text_styles = set(text_styles or [TextStyle.Normal])
        self.style = style
        self.text = text
        self.text_xml = self._generate_xml()

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, val: str) -> None:
        if self.type == ElementType.Space:
            self._text = " "
            return

        if self.type == ElementType.Newline:
            self._text = ""
            return

        self._text = val

    @property
    def style(self) -> ParagraphStyle:
        return self._style

    @style.setter
    def style(self, val: ParagraphStyle) -> None:
        match self.type:
            case ElementType.Space:
                _style = PSTYLES["SmallParagraph"]
            case ElementType.TerminologyHeader:
                _style = PSTYLES["TerminologyHeader"]
            case _:
                _style = val

        for text_style in self.text_styles:
            match text_style:
                case TextStyle.Superscript:
                    _style = _style.superscripted
                case TextStyle.Subscript:
                    _style = _style.subscripted
                case TextStyle.Strong:
                    _style = _style.bold
                case TextStyle.Italic:
                    _style = _style.italic
                case TextStyle.Link:
                    _style = _style.link
                case _:
                    pass

        self._style = _style

    @property
    def font_size(self) -> float:
        return self.style.font_size

    @property
    def font_name(self) -> str:
        return self.style.font_name

    @property
    def width(self) -> float:
        if self.type == ElementType.Newline:
            return INNER_WIDTH - 0.01

        _width = stringWidth(self.text, self.font_name, self.font_size)
        _width += self.style.x_padding
        return _width

    @property
    def height(self) -> float:
        return self.style.leading

    def _generate_xml(self) -> str:
        xml = escape(self.text)
        if TextStyle.Strong in self.text_styles:
            xml = f"<b>{xml}</b>"

        if TextStyle.Italic in self.text_styles:
            xml = f"<i>{xml}</i>"

        if TextStyle.Pre in self.text_styles:
            xml = f"<pre>{xml}</pre>"

        if TextStyle.Link in self.text_styles:
            if self.link is not None:
                href = f"href=\"{self.link}\""
            else:
                href = ""

            xml = f"<link {href}>{xml}</link>"

        return xml

    def add_text_style(self, style: TextStyle) -> None:
        """Adds `style` to this elements set of text styles.

        This method will have no effect if `style` already exists in this
        elements set of text styles.
        """

        self.text_styles.add(style)

    def is_styled(self) -> bool:
        """Determines if this element uses a custom (non-default) styling."""

        return self.style.name != DEF_PSTYLE.name

    def copy(
        self,
        text: str | None = None,
        type: ElementType | None = None,
        styles: list[TextStyle] | None = None,
        style: ParagraphStyle | None = None,
        link: str | None = None
    ) -> ParagraphElement:
        """Creates a copy of this element.

        Attributes of the copy will be overwritten by any supplied arguments
        of this method.
        """

        return ParagraphElement(
            text=text or self.text,
            type=type or self.type,
            text_styles=styles or self.text_styles,
            style=style or self.style,
            link=link or self.link
        )

    def join(self, *elements: ParagraphElement) -> None:
        """Joins each element in `element` into this element. Elements are
        joined by iteratively appending the joining elements text to this
        element.

        Raises:
            ElementJoinError
                : An element in `elements` cannot be joined with this element.
        """

        for element in elements:
            if self.type == ElementType.Reference:
                raise ElementJoinError("Cannot join reference tags")

            if element.type == ElementType.Space:
                self.text += " "
                continue

            if self.type != element.type:
                raise ElementJoinError("Cannot join elements with different types")

            if self.text_styles != element.text_styles:
                raise ElementJoinError("Cannot join elements with different text styles")
    
            if self.link != element.link:
                raise ElementJoinError("Cannot join elements with different links")

            self.text += element.text

    def split(self, size: int = 1) -> list[ParagraphElement]:
        """Returns the result of splitting this paragraph element into several
        paragraph elements. This instance will not be modified.

        Split elements will be grouped into subsets of `size` elements and each
        group will be joined. If the amount of split elements is not divisible
        by `size`, any remaining elements will be joined.

        Args:
            - size (int)
                : Specifies the subset group size for element joining.
                If `size == 1`, no elements will be joined.
        """

        words = self.text.split()
        word_count = len(words)
        if word_count == 0:
            return []
        elif word_count == 1:
            return [self]

        if self.text == "":
            return []

        if self.text[0] == " ":
            words[0] = f" {words[0]}"

        if len(self.text) > 1 and self.text[-1] == " ":
            words[-1] = f"{words[-1]} "

        elements: list[ParagraphElement] = []
        if word_count == 2:
            elements.append(self.copy(f"{words[0]} "))
            elements.append(self.copy(words[1]))
        else:
            for i, word in enumerate(words):
                if i == 0:
                    elem_cpy = self.copy(word)
                else:
                    elem_cpy = self.copy(f" {word}")

                elements.append(elem_cpy)

        elem_frags = list(filter(lambda e: e.text != "", elements))
        if size >= len(elem_frags):
            return [self]

        if size == 1:
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
            if all([elem_type == ElementType.Space for elem_type in elem_types]):
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

    def _add(self, element: ParagraphElement) -> None:
        if self.max_width is not None and element.width + self.width > self.max_width:
            raise WidthExceededError(f"Max width of {self.max_width} exceeded")

        try:
            self._elements[-1].join(element)
        except (IndexError, ElementJoinError):
            self._elements.append(element)

    def add(self, element: ParagraphElement) -> None:
        if element.text == "":
            return

        if self.style is not None and element.type != ElementType.Reference:
            element.style = self.style

        if self.elements == []:
            new_elem = element.copy(element.text.lstrip())
        else:
            new_elem = element

        if element.type == ElementType.Reference:
            self._add(ParagraphElement(type=ElementType.Space))
            self._add(new_elem)
            self._add(ParagraphElement(type=ElementType.Space))
        else:
            self._add(new_elem)

    def get_min_width(self, size: int = 1) -> float:
        split_elems: list[ParagraphElement] = []
        for elem in self.elements:
            split_elems.extend(elem.split(size))

        if split_elems == []:
            return self.width

        return max([elem.width for elem in split_elems])

    def pop(self, index: int = -1) -> ParagraphElement:
        return self._elements.pop(index)
