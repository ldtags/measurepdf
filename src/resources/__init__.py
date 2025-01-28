import os
import json
from typing import Any


_PATH = os.path.abspath(os.path.dirname(__file__))


def get_path(file_name: str, exists: bool = True) -> str:
    file_path = os.path.join(_PATH, file_name)
    if exists and not os.path.exists(file_path):
        raise FileNotFoundError(f"No resource named {file_name} exists")

    return file_path


def get_json(file_name: str) -> dict[str, Any]:
    _, ext = os.path.splitext(file_name)
    if ext != ".json":
        raise RuntimeError(f"File {file_name} must be a JSON file")

    file_path = get_path(file_name, exists=True)
    with open(file_path, "r") as fp:
        return json.load(fp)
