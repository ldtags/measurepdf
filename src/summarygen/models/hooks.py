from typing import Any

from src.utils import JSONObject


class ObjectInfo(JSONObject):
    def __init__(self, _json: str | dict[str, Any]):
        JSONObject.__init__(self, _json)
        self.id = self.get('id', str)
        self.title = self.get('title', str)
        self.ctype_id = self.get('ctype_id', int)
        self.verbose_name = self.get('verbose_name', str)
        self.verbose_name_plural = self.get('verbose_name_plural', str)
        self.change_url = self.get('change_url', str)


class RefObjectInfo(ObjectInfo):
    def __init__(self, _json: str | dict[str, Any]):
        ObjectInfo.__init__(self, _json)
        self.preview_url = self.get('preview_url', str)
        self.ref_type = self.get('refType', str)


class ReferenceTag(JSONObject):
    def __init__(self, _json: str | dict[str, Any]):
        JSONObject.__init__(self, _json)
        self.obj_info = self.get('objInfo', RefObjectInfo)
        self.ref_type = self.get('refType', str)
        self.obj_deleted = self.get('objDeleted', bool)
        self.title = self.obj_info.title.upper()


class VTConfig(JSONObject):
    def __init__(self, _json: str | dict[str, Any]):
        JSONObject.__init__(self, _json)
        self.ver = self.get('ver', int)
        self.cids = self.get('cids', list[str])


class VTObjectInfo(ObjectInfo):
    def __init__(self, _json: str | dict[str, Any]):
        ObjectInfo.__init__(self, _json)
        self.api_name_unique = self.get('api_name_unique', str)
        self.vtconf = self.get('vt_conf', VTConfig | None)

    @property
    def possible_names(self) -> list[str]:
        return [self.api_name_unique, self.title, self.verbose_name]


class EmbeddedValueTableTag(JSONObject):
    def __init__(self, _json: str | dict[str | Any]):
        JSONObject.__init__(self, _json)
        self.obj_info = self.get('objInfo', VTObjectInfo)
        self.obj_deleted = self.get('objDeleted', bool)


class ImgObjectInfo(ObjectInfo):
    def __init__(self, _json: str | dict[str, Any]):
        ObjectInfo.__init__(self, _json)
        self.preview_url = self.get('preview_url', str)
        self.width = self.get('width', int)
        self.image_url = self.get('image_url', str)


class EmbeddedImage(JSONObject):
    def __init__(self, _json: str | dict[str, Any]):
        JSONObject.__init__(self, _json)
        self.obj_info = self.get('objInfo', ImgObjectInfo)
        self.caption = self.get('caption', str)
        self.align = self.get('align', str)
