import os


_ROOT = os.path.abspath(os.path.dirname(__file__))


def asset_path(file_name: str, *parent_dirs: str) -> str:
    file_path = os.path.join(_ROOT, 'assets', *parent_dirs, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'no asset named {file_name} exists')
    return file_path
