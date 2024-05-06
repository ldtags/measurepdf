from __future__ import annotations
import json
from enum import Enum

from src.utils import getc


class ElemType(Enum):
    TEXT = 'text'
    REF = 'ref'


class TextStyle(Enum):
    NORMAL = 'normal'
    STRONG = 'strong'
    SUP = 'sup'
    SUB = 'sub'


class ParagraphElement:
    def __init__(self,
                 text: str,
                 type: ElemType=ElemType.TEXT,
                 styles: list[TextStyle] | None=None):
        self.text = text
        self.type = type
        self.styles = styles or [TextStyle.NORMAL]

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
        super().__init__(f' {self.obj_info.title.upper()} ',
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
