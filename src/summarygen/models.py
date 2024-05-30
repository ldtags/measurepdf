from __future__ import annotations
import json
from enum import Enum
from reportlab.pdfbase.pdfmetrics import stringWidth

from src.utils import getc
from src.exceptions import ElementJoinError
from src.summarygen.styling import DEF_PSTYLE


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
                 styles: list[TextStyle] | None=None):
        self.text = text
        self.type = type
        self.styles = styles or [TextStyle.NORMAL]

    @property
    def width(self) -> float:
        if TextStyle.SUB in self.styles:
            font_size = DEF_PSTYLE.sub_size
        elif TextStyle.SUP in self.styles:
            font_size = DEF_PSTYLE.sup_size
        else:
            font_size = DEF_PSTYLE.font_size

        font_name = DEF_PSTYLE.font_name
        if TextStyle.STRONG in self.styles:
            font_name += 'B'
        if TextStyle.ITALIC in self.styles:
            font_name += 'I'

        return stringWidth(self.text, font_name, font_size)

    def join(self, element: ParagraphElement):
        if self.type == ElemType.REF:
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
             styles: list[TextStyle] | None=None
            ) -> ParagraphElement:
        return ParagraphElement(text or self.text,
                                type or self.type,
                                styles or self.styles)


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
            ref_copy.text = f' {text.upper()} '
        return ref_copy


class VTConfig:
    def __init__(self, json_obj: dict):
        self.ver = getc(json_obj, 'ver', int)
        self.cids = getc(json_obj, 'cids', list[str])


class VTObjectInfo(ObjectInfo):
    def __init__(self, json_obj: dict):
        super().__init__(json_obj)
        self.api_name_unique = getc(json_obj, 'api_name_unique', str)
        self.vtconf = getc(json_obj, 'vt_conf', VTConfig)


class EmbeddedValueTableTag:
    def __init__(self, json_str: str):
        self._json_str = json_str
        self._json: dict = json.loads(json_str)
        self.obj_info = getc(self._json, 'objInfo', VTObjectInfo)
        self.obj_deleted = getc(self._json, 'objDeleted', bool)
