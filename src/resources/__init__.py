import os

_PATH = os.path.abspath(os.path.dirname(__file__))

def get_path(file_name: str) -> str:
    file_path = os.path.join(_PATH, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'no resource named {file_name} exists')
    return file_path
