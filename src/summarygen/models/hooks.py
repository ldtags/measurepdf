from typing import Any
import datetime as dt

from src.utils import JSONObject


def convert_from_utc(date_string: str) -> dt.datetime:
    return dt.datetime.strptime(
        date_string,
        r"%Y-%m-%dT%H:%M:%SZ"
    ).replace(
        tzinfo=dt.timezone.utc
    )


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


class Revision(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.version = self.get("version", float)
        self.publish_date = convert_from_utc(self.get("publish_date", str))
        self.description = self.get("description", str)
        self.owner = self.get("owner", str)


class KeyTerminology(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.name = self.get("name", str)
        self.api_name = self.get("api_name", str | None)
        self.content = self.get("content", str)
        self.contains_table = self.get("contains_table", bool)
        self.columns = self.get("columns", list[str] | None)
        self.column_mappings = self.get("column_mappings", dict[str, str] | None)
        self.data = self.get("data", list[list[str]] | None)
        self.append = self.get("append", str | None)
        self.sub_sections = self.get("sub_sections", list[KeyTerminology] | None)
        self.row_split = self.get("row_split", int | None, None)
        self.caption = self.get("caption", str | None, None)

        for i, section in enumerate(self.sub_sections or []):
            self.sub_sections[i] = KeyTerminology(section)

    def requires_etrm_table(self) -> bool:
        if self.api_name is None:
            return False

        if self.columns is None:
            return False

        if self.data is not None and self.append is None:
            return False

        return True

    def get_table_headers(self) -> list[str] | None:
        if self.columns is None:
            return None

        headers = self.columns.copy()
        if self.column_mappings is None:
            return headers

        for i, header in enumerate(headers):
            mapping = self.column_mappings.get(header)
            if mapping is not None:
                headers[i] = mapping

        return headers
