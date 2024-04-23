import os

_ROOT = os.path.abspath(os.path.dirname(__file__))

def get_path(file_name: str) -> str:
    _path = os.path.join(_ROOT, file_name)
    if not os.path.exists(_path):
        raise FileNotFoundError(f'no resource named {file_name} exists')
    return _path
