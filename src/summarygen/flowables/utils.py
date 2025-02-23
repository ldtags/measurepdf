from src.summarygen.styles import (
    ParagraphStyle,
    INNER_WIDTH
)
from src.summarygen.exceptions import WidthExceededError
from src.summarygen.models import (
    ParagraphElement,
    ElementLine
)


def split_word(
    element: ParagraphElement,
    rem_width: float = INNER_WIDTH,
    max_width: float = INNER_WIDTH
) -> list[ParagraphElement]:
    width = rem_width
    word: str = element.text
    frags: list[ParagraphElement] = []
    i = 0
    while i < len(word):
        j = i + 1
        elem_frag = element.copy(text=word[i:j])
        while j < len(word) and elem_frag.width < width:
            j += 1
            elem_frag = element.copy(text=word[i:j])

        if j == len(word) and elem_frag.width < width:
            frags.append(elem_frag)
            break

        frags.append(element.copy(text=word[i:j - 1]))
        i = j - 1
        width = max_width

    return frags


def wrap_elements(
    elements: list[ParagraphElement],
    max_width: float = INNER_WIDTH,
    style: ParagraphStyle | None = None,
    strict: bool = False
) -> list[ElementLine]:
    element_lines: list[ElementLine] = []
    current_line = ElementLine(max_width=max_width, style=style)
    for element in elements:
        try:
            current_line.add(element)
        except WidthExceededError:
            for elem in element.split():
                try:
                    current_line.add(elem)
                except WidthExceededError:
                    if elem.width > max_width and strict:
                        avail_width = max_width - current_line.width
                        word_frags = split_word(elem, avail_width, max_width)
                        current_line.add(word_frags[0])
                        element_lines.append(current_line)
                        if len(word_frags) > 1:
                            for word_frag in word_frags[1:len(word_frags)]:
                                current_line = ElementLine(
                                    max_width=max_width,
                                    style=style
                                )

                                current_line.add(word_frag)
                        else:
                            current_line = ElementLine(
                                max_width=max_width,
                                style=style
                            )
                    elif elem.width <= max_width:
                        element_lines.append(current_line)
                        current_line = ElementLine(
                            max_width=max_width,
                            style=style
                        )
                        current_line.add(elem)
                    else:
                        current_line.max_width = None
                        current_line.add(elem)
                        element_lines.append(current_line)
                        current_line = ElementLine(
                            max_width=max_width,
                            style=style
                        )

    if len(current_line) != 0:
        element_lines.append(current_line)

    return element_lines
