__version__ = "1.0.0"
__date__ = "March 10th, 2025"


import os
import sys
import logging
import platform
from datetime import datetime as dt


match platform.system():
    case "Linux" | "Darwin" | "Windows" as system:
        _SYSTEM = system
    case other:
        raise RuntimeError(f"Unknown platform: {other}")


START_TIME = dt.now()

_ROOT = os.path.abspath(os.path.dirname(__file__))

IS_DEBUG_MODE: bool = False

TMP_DIR = os.path.join(_ROOT, "assets", "images", "tmp")

def _configure_logger() -> None:
    date_str = dt.now().strftime(r"%Y-%m-%d_%H-%M-%S")
    logging.basicConfig(
        format="%(asctime)s [%(levelname)-8.8s] %(message)s",
        datefmt=r"%m/%d/%Y %I:%M:%S %p",
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(f"logs/{date_str}.log", mode="w"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def asset_path(file_name: str, *parent_dirs: str) -> str:
    file_path = os.path.join(_ROOT, "assets", *parent_dirs, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No asset named {file_name} exists")

    return file_path


def src_path(file_name: str) -> str:
    file_path = os.path.join(_ROOT, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No file named {file_name} exists in {_ROOT}")

    return file_path


def set_debug_mode(val: bool) -> None:
    """Sets the global `IS_DEBUG_MODE` variable.

    Use this when applying styles or logging that is debug only.
    """

    global IS_DEBUG_MODE

    IS_DEBUG_MODE = val


_configure_logger()
