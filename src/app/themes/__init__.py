import os
from typing import Literal

from src.exceptions import GUIError


_DIR_PATH = os.path.abspath(os.path.dirname(__file__))


_THEME = Literal['default']
def get_theme(theme: _THEME) -> str:
    file_name = f'{theme}.json'
    file_path = os.path.join(_DIR_PATH, file_name)
    if not os.path.exists(file_path):
        raise GUIError(f'{theme} is not a recognized local theme')
    norm_path = os.path.normpath(file_path)
    return norm_path
