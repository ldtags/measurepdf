from __future__ import annotations
import math
from abc import ABCMeta, abstractmethod
from PIL import Image

from src import assets
from src.summarygen import utils
from src.summarygen.types import _TableSpan
from src.summarygen.models.enums import Alignment, TextStyle
from src.summarygen.models.general import BulletOption
from src.summarygen.models.elements import ParagraphElement
from src.summarygen.models.constants import (
    DEFAULT_INDENT_LEVEL,
    DEFAULT_INDENT_SIZE,
    DEFAULT_BULLET_INDENT_SIZE,
    DEFAULT_SPACE_BEFORE,
    DEFAULT_SPACE_AFTER,
    DEFAULT_ALIGNMENT,
    CIRCLE_BULLET
)
from src.summarygen.exceptions import SummaryGenError


class HTMLSection(metaclass=ABCMeta):
    @abstractmethod
    def __init__(
        self,
        indent_level: int = DEFAULT_INDENT_LEVEL,
        indent_size: int = DEFAULT_INDENT_SIZE,
        space_before: int = DEFAULT_SPACE_BEFORE,
        space_after: int = DEFAULT_SPACE_AFTER,
        alignment: Alignment = DEFAULT_ALIGNMENT
    ) -> None:
        self.indent_level = indent_level
        self.indent_size = indent_size
        self.space_before = space_before
        self.space_after = space_after
        self.alignment = alignment

    @property
    def indent_level(self) -> int:
        return self._indent_level

    @indent_level.setter
    def indent_level(self, val: int) -> None:
        if val < 0:
            raise SummaryGenError(f"Indent level must be a non-negative integer: {val}")

        self._indent_level = val

    @property
    def indent_size(self) -> int:
        return self._indent_size

    @indent_size.setter
    def indent_size(self, val: int) -> None:
        if val < 0:
            raise SummaryGenError(f"Indent size must be a non-negative integer: {val}")

        self._indent_size = val

    @property
    def space_before(self) -> int:
        return self._space_before

    @space_before.setter
    def space_before(self, val: int) -> None:
        if val < 0:
            raise SummaryGenError(f"Space before must be a non-negative integer: {val}")

        self._space_before = val

    @property
    def space_after(self) -> int:
        return self._space_after

    @space_after.setter
    def space_after(self, val: int) -> None:
        if val < 0:
            raise SummaryGenError(f"Space after must be a non-negative integer: {val}")

        self._space_after = val

    @property
    @abstractmethod
    def height(self) -> float:
        return 0

    @property
    @abstractmethod
    def width(self) -> float:
        return 0


class ParagraphSection(HTMLSection):
    """Defines an HTML paragraph section.

    Contains elements that will be joined into a single paragraph.
    """

    def __init__(
        self,
        elements: list[ParagraphElement],
        indent_level: int = DEFAULT_INDENT_LEVEL,
        indent_size: int = DEFAULT_INDENT_SIZE,
        space_before: int = DEFAULT_SPACE_BEFORE,
        space_after: int = DEFAULT_SPACE_AFTER,
        alignment: Alignment = DEFAULT_ALIGNMENT
    ) -> None:
        super().__init__(
            indent_level=indent_level,
            indent_size=indent_size,
            space_before=space_before,
            space_after=space_after,
            alignment=alignment
        )

        self.elements = elements

    def join(self, section: ParagraphSection) -> None:
        """Joins `section` with this element.

        A `ParagraphSection` join is the process of adding all paragraph
        elements from `section` to this instance. No `ParagraphElement`
        instances will be joined.
        """

        self.elements.extend(section.elements)

    def add_style(self, style: TextStyle) -> None:
        """Adds `style` to each `ParagraphElement` in this objects elements.

        If an element already has the style `style`, that element will not be
        modified.
        """

        for element in self.elements:
            element.add_text_style(style)

    @property
    def height(self) -> float:
        height = max([element.height for element in self.elements])
        return height

    @property
    def width(self) -> float:
        width = max([element.width for element in self.elements])
        return width


class ListSection(HTMLSection):
    """Defines an HTML unordered list section.

    Contains HTML sections that define the list items.

    If a `ListSection` is contained within the `list_items` of this object, it
    will be treated as a sub-list that increments the list level.
    """

    def __init__(
        self,
        list_items: list[list[HTMLSection]],
        bullet_option: BulletOption = CIRCLE_BULLET,
        indent_level: int = DEFAULT_INDENT_LEVEL,
        indent_size: int = DEFAULT_INDENT_SIZE,
        bullet_indent_size: int = DEFAULT_BULLET_INDENT_SIZE,
        space_before: int = 4,
        space_after: int = 5,
        alignment: Alignment = DEFAULT_ALIGNMENT
    ) -> None:
        super().__init__(
            indent_level=indent_level,
            indent_size=indent_size,
            space_before=space_before,
            space_after=space_after,
            alignment=alignment
        )

        self.list_items = list_items
        self.bullet_option = bullet_option
        self.bullet_indent_size = bullet_indent_size

    @property
    def height(self) -> float:
        heights: list[float] = []
        for list_item in self.list_items:
            heights.append(max([section.height for section in list_item]))

        return math.fsum(heights)

    @property
    def width(self) -> float:
        widths: list[float] = []
        for list_item in self.list_items:
            widths.append(max([section.width for section in list_item]))

        return max(widths)


class ImageSection(HTMLSection):
    """Defines an HTML img section.

    An `ImageSection` element will be created whenever an `img` tag appears
    in the HTML.
    """

    def __init__(
        self,
        url: str,
        indent_level: int = DEFAULT_INDENT_LEVEL,
        indent_size: int = DEFAULT_INDENT_SIZE,
        space_before: int = DEFAULT_SPACE_BEFORE,
        space_after: int = DEFAULT_SPACE_AFTER,
        alignment: Alignment = Alignment.Center
    ) -> None:
        super().__init__(
            indent_level=indent_level,
            indent_size=indent_size,
            space_before=space_before,
            space_after=space_after,
            alignment=alignment
        )

        self.url = url
        if url.startswith("./"):
            self.img_path = assets.get_path(url[2:])
        else:
            self.img_path = utils.download_image(url)

        self._image_width, self._image_height = Image.open(self.img_path).size

    @property
    def height(self) -> float:
        return float(self._image_height)

    @property
    def width(self) -> float:
        return float(self._image_width)


class TableSection(HTMLSection):
    """Defines an HTML table section.

    Headers are comprised of anything within a <th> tag.
    Cells are comprised of anything within a <td> tag.
    """

    def __init__(
        self,
        rows: list[list[list[HTMLSection] | None]],
        headers: list[list[list[HTMLSection] | None]] | None = None,
        spans: list[_TableSpan] | None = None,
        indent_level: int = DEFAULT_INDENT_LEVEL,
        indent_size: int = DEFAULT_INDENT_SIZE,
        space_before: int = DEFAULT_SPACE_BEFORE,
        space_after: int = DEFAULT_SPACE_AFTER,
        alignment: Alignment = Alignment.Center
    ) -> None:
        super().__init__(
            indent_level=indent_level,
            indent_size=indent_size,
            space_before=space_before,
            space_after=space_after,
            alignment=alignment
        )

        self.headers = headers or []
        self.rows = rows
        self.spans = spans or []

    @property
    def height(self) -> float:
        height: float = 0
        for row in [*self.headers, *self.rows]:
            heights: list[float] = []
            for item in row:
                heights.append(math.fsum([section.height for section in item]))

            height += max(heights)

        return height

    @property
    def width(self) -> float:
        width: float = 0
        for row in [*self.headers, *self.rows]:
            row_width: float = 0
            for item in row:
                row_width += max([section.width for section in item])

            width = max(width, row_width)

        return width
