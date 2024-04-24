import os
import sys

_ROOT = os.path.abspath(os.path.dirname(__file__))

def asset_path(file_name: str, *parent_dirs: str) -> str:
    return os.path.join(_ROOT, 'assets', *parent_dirs, file_name)
