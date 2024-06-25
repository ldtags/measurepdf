from __future__ import annotations
import math
from reportlab.platypus import Flowable, Table, KeepTogether

from src.exceptions import WidthExceededError, ElementJoinError
from src.summarygen.models import ParagraphElement, ElemType
from src.summarygen.styling import (
    INNER_WIDTH,
    INNER_HEIGHT,
    BetterParagraphStyle
)


class ElementLine:
    def __init__(self,
                 elements: list[ParagraphElement] | None=None,
                 max_width: float | None=INNER_WIDTH,
                 style: BetterParagraphStyle | None=None):
        self.style = style
        self.max_width = max_width
        self.elements: list[ParagraphElement] = []
        self.__index: int = 0

        if elements is not None:
            for element in elements:
                self.add(element)

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
            return ''
        return ''.join([elem.text for elem in self.elements])

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
        if (self.max_width is not None
                and element.width + self.width > self.max_width):
            raise WidthExceededError(f'Max width of {self.max_width} exceeded')

        try:
            self.elements[-1].join(element)
        except (IndexError, ElementJoinError):
            self.elements.append(element)

    def add(self, element: ParagraphElement):
        if element.text == '':
            return

        if self.style is not None:
            element.style = self.style

        if self.elements == []:
            new_elem = element.copy(element.text.lstrip())
        else:
            new_elem = element

        if new_elem.type == ElemType.REF:
            self.__add(ParagraphElement(' ', type=ElemType.SPACE))
            self.__add(new_elem)
            self.__add(ParagraphElement(' ', type=ElemType.SPACE))
        else:
            self.__add(new_elem)

    def pop(self, index: int=-1) -> ParagraphElement:
        return self.elements.pop(index)


class Story:
    def __init__(self):
        self.contents: list[Flowable] = []
        self.height: float = 0
        self.page_height: float = 0

    def add(self, flowables: Flowable | list[Flowable]):
        if isinstance(flowables, Flowable):
            flowables = [flowables]
        for flowable in flowables:
            self.contents.append(flowable)
            if isinstance(flowable, Table):
                height = math.fsum(flowable._rowHeights)
            else:
                height = flowable._fixedHeight
            self.height += height
            if isinstance(flowable, KeepTogether):
                if self.page_height + height > INNER_HEIGHT:
                    self.page_height = height
                else:
                    self.page_height += height
            elif self.page_height + height > INNER_HEIGHT:
                margin = INNER_HEIGHT - self.page_height
                self.page_height = height - margin
            else:
                self.page_height += height

    def clear(self):
        self.contents = []
        self.height = 0
        self.page_height = 0
