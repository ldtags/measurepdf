import os
import sys

if getattr(sys, 'frozen', False):
    _ROOT = sys._MEIPASS
else:
    _ROOT = os.path.abspath(os.path.dirname(__file__))

def asset_path(file_name: str, *parent_dirs: str) -> str:
    if getattr(sys, 'frozen', False):
        return os.path.join(_ROOT, 'src', 'assets', *parent_dirs, file_name)
    return os.path.join(_ROOT, 'assets', *parent_dirs, file_name)
