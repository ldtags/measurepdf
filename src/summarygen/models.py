from __future__ import annotations
import json
from enum import Enum
from reportlab.pdfbase.pdfmetrics import stringWidth

from src.utils import getc
from src.exceptions import ElementJoinError
from src.summarygen.styling import DEF_PSTYLE, BetterParagraphStyle, PSTYLES


class ElemType(Enum):
    TEXT = 'text'
    REF = 'ref'
    SPACE = 'space'


class TextStyle(Enum):
    NORMAL = 'normal'
    STRONG = 'strong'
    ITALIC = 'em'
    SUP = 'sup'
    SUB = 'sub'


class ParagraphElement:
    """Defines an element found in an HTML document."""

    def __init__(self,
                 text: str,
                 type: ElemType=ElemType.TEXT,
                 styles: list[TextStyle] | None=None,
                 style: BetterParagraphStyle | None=None):
        self.text = text
        self.type = type
        self.styles = styles or [TextStyle.NORMAL]
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
                case TextStyle.NORMAL:
                    pass
                case x:
                    raise ValueError(f'{x} is not a valid TextStyle')
            cur_styles.append(style)
        return text

    @property
    def style(self) -> BetterParagraphStyle:
        if self.__style is not None:
            return self.__style

        if self.type == ElemType.REF:
            return PSTYLES['ReferenceTag']

        if self.type == ElemType.SPACE:
            return PSTYLES['SmallParagraph']

        for style in self.styles:
            match style:
                case TextStyle.SUP:
                    return DEF_PSTYLE.superscripted
                case TextStyle.SUB:
                    return DEF_PSTYLE.subscripted
                case TextStyle.STRONG:
                    return DEF_PSTYLE.bold
                case TextStyle.ITALIC:
                    return DEF_PSTYLE.italic
                case _:
                    pass
        return DEF_PSTYLE

    @style.setter
    def style(self, _style: BetterParagraphStyle):
        self.__style = _style

    @property
    def font_size(self) -> float:
        return self.style.font_size

    @property
    def font_name(self) -> str:
        return self.style.font_name

    @property
    def width(self) -> float:
        return stringWidth(self.text, self.font_name, self.font_size)

    @property
    def height(self) -> float:
        return self.style.leading

    def split(self) -> list[ParagraphElement]:
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
        return list(filter(lambda e: e.text != '', elements))

    def join(self, element: ParagraphElement):
        if self.type == ElemType.REF or self.type == ElemType.SPACE:
            raise ElementJoinError('Cannot join reference tags')

        if self.type != element.type:
            raise ElementJoinError('Cannot join elements with different types')

        if self.styles != element.styles:
            raise ElementJoinError('Cannot join elements with different'
                                   ' styles')

        self.text += element.text

    def copy(self,
             text: str | None=None,
             type: ElemType | None=None,
             styles: list[TextStyle] | None=None,
             style: BetterParagraphStyle | None=None
            ) -> ParagraphElement:
        return ParagraphElement(text or self.text,
                                type or self.type,
                                styles or self.styles,
                                style or self.style)


class ObjectInfo:
    def __init__(self, json_obj: dict):
        self.id = getc(json_obj, 'id', str)
        self.title = getc(json_obj, 'title', str)
        self.ctype_id = getc(json_obj, 'ctype_id', int)
        self.verbose_name = getc(json_obj, 'verbose_name', str)
        self.verbose_name_plural = getc(json_obj, 'verbose_name_plural', str)
        self.change_url = getc(json_obj, 'change_url', str)


class RefObjectInfo(ObjectInfo):
    def __init__(self, json_obj: dict):
        super().__init__(json_obj)
        self.preview_url = getc(json_obj, 'preview_url', str)
        self.ref_type = getc(json_obj, 'refType', str)


class ReferenceTag(ParagraphElement):
    def __init__(self, json_str: str):
        self._json_str = json_str
        json_obj: dict = json.loads(json_str)
        self.obj_info = getc(json_obj, 'objInfo', RefObjectInfo)
        self.ref_type = getc(json_obj, 'refType', str)
        self.obj_deleted = getc(json_obj, 'objDeleted', bool)
        super().__init__(self.obj_info.title.upper(),
                         ElemType.REF,
                         [TextStyle.STRONG])

    def copy(self,
             text: str | None=None,
             json_str: str | None=None
            ) -> ReferenceTag:
        ref_copy = ReferenceTag(json_str or self._json_str)
        if text != None:
            ref_copy.obj_info.title = text.lower()
            ref_copy.obj_info.id = text.lower()
            ref_copy.text = text.upper()
        return ref_copy


class VTConfig:
    def __init__(self, json_obj: dict):
        self.ver = getc(json_obj, 'ver', int)
        self.cids = getc(json_obj, 'cids', list[str])


class VTObjectInfo(ObjectInfo):
    def __init__(self, json_obj: dict):
        super().__init__(json_obj)
        self.api_name_unique = getc(json_obj, 'api_name_unique', str)
        self.vtconf = getc(json_obj, 'vt_conf', VTConfig | None)


class EmbeddedValueTableTag:
    def __init__(self, json_str: str):
        self._json_str = json_str
        self._json: dict = json.loads(json_str)
        self.obj_info = getc(self._json, 'objInfo', VTObjectInfo)
        self.obj_deleted = getc(self._json, 'objDeleted', bool)


class ImgObjectInfo(ObjectInfo):
    def __init__(self, json_obj: dict):
        super().__init__(json_obj)
        self.preview_url = getc(json_obj, 'preview_url', str)
        self.width = getc(json_obj, 'width', int)
        self.image_url = getc(json_obj, 'image_url', str)


class EmbeddedImage:
    def __init__(self, json_str: str):
        self._json_str = json_str
        self._json: dict = json.loads(json_str)
        self.obj_info = getc(self._json, 'objInfo', ImgObjectInfo)
        self.caption = getc(self._json, 'caption', str)
        self.align = getc(self._json, 'align', str)
