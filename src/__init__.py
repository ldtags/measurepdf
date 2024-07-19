import os
import logging
import platform
from datetime import datetime


match platform.system():
    case 'Linux' | 'Darwin' | 'Windows' as system:
        _SYSTEM = system
    case other:
        raise RuntimeError(f'Unknown platform: {other}')


_NOW = datetime.now()


_ROOT = os.path.abspath(os.path.dirname(__file__))


_LOG_FILE_NAME = 'summarygen.log'
logging.basicConfig(filename=_LOG_FILE_NAME,
                    level=logging.INFO,
                    filemode='w')


def asset_path(file_name: str, *parent_dirs: str) -> str:
    file_path = os.path.join(_ROOT, 'assets', *parent_dirs, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'No asset named {file_name} exists')
    return file_path


def src_path(file_name: str) -> str:
    file_path = os.path.join(_ROOT, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'No file named {file_name} exists in {_ROOT}')
    return file_path
