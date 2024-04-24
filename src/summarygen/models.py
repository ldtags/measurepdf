import json
from typing import Any
from reportlab.platypus import TableStyle

from src.utils import getc


class ObjectInfo:
    def __init__(self, json_obj: dict):
        self.id = getc(json_obj, 'id', str | None)
        self.title = getc(json_obj, 'title', str)
        self.ctype_id = getc(json_obj, 'ctype_id', int)
        self.verbose_name = getc(json_obj, 'verbose_name', str)
        self.verbose_name_plural = getc(json_obj, 'verbose_name_plural', str)
        self.change_url = getc(json_obj, 'change_url', str)
        self.preview_url = getc(json_obj, 'preview_url', str)


class ReferenceTag:
    def __init__(self, json_str: str):
        json_obj: dict = json.loads(json_str)
        self.obj_info = getc(json_obj, 'objInfo', ObjectInfo)
        self.ref_type = getc(json_obj, 'refType', str)
        self.obj_deleted = getc(json_obj, 'objDeleted', bool)


class NamedTableStyle(TableStyle):
    def __init__(self,
                 name: str,
                 cmds: Any | None=None,
                 parent: Any | None=None,
                 **kwargs):
        super().__init__(cmds, parent, **kwargs)

        self.name = name
        self.font_size: float = 12
        self.font_name: str = 'Helvetica'
        for cmd in cmds:
            match cmd[0]:
                case 'FONTSIZE':
                    self.font_size = float(cmd[3])
                case 'FONTNAME':
                    self.font_name = str(cmd[3])