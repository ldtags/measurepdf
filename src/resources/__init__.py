__all__ = [
    # Models
    "Revision",
    "KeyTerminology",
    "KeyTerminologySection",
    "SectionDescription",
    "SunsettedMeasure",
    "SunsettedMeasureCollection",
    "SunsettedMeasuresSection",

    # Methods
    "get_api_key",
    "get_revisions",
    "get_key_terminology",
    "get_section_description",
    "get_introduction_html",
    "get_data_table_html",
    "get_use_category_intro_html",
]


import os
import re
import json
from typing import Any, Literal
from configparser import ConfigParser

from .models import (
    Revision,
    KeyTerminology,
    KeyTerminologySection,
    SectionDescription,
    SunsettedMeasure,
    SunsettedMeasureCollection,
    SunsettedMeasuresSection
)


_PATH = os.path.abspath(os.path.dirname(__file__))


def get_path(file_name: str, exists: bool = True) -> str:
    file_path = os.path.join(_PATH, file_name)
    if exists and not os.path.exists(file_path):
        raise FileNotFoundError(f"No resource named {file_name} exists")

    return file_path


def get_api_key(role: Literal["user", "admin"] = "user") -> str:
    match role:
        case "user":
            source = "etrm"
        case "admin":
            source = "etrm-admin"
        case other:
            raise RuntimeError(f"Invalid eTRM role: {other}")

    config = ConfigParser()
    config.read(get_path("data/config.ini"))
    token_type = config[source]["type"]
    token = config[source]["token"]
    return f"{token_type} {token}"


def get_json(file_name: str) -> dict[str, Any]:
    _, ext = os.path.splitext(file_name)
    if ext != ".json":
        raise RuntimeError(f"File {file_name} must be a JSON file")

    file_path = get_path(file_name, exists=True)
    with open(file_path, "r") as fp:
        return json.load(fp)


def get_revisions() -> list[Revision]:
    data = get_json("data/revisions.json")
    return [
        Revision(revision)
        for revision
        in data.get("revisions", [])
    ]


def get_key_terminology() -> KeyTerminologySection:
    data = get_json("data/key_terminology.json")
    return KeyTerminologySection(data)


def get_section_description(measure_id: str) -> SectionDescription | None:
    data = get_json("data/section_descriptions.json")
    desc_json = data.get(measure_id)
    if desc_json is None:
        return None

    return SectionDescription(desc_json)


def ensure_html_file(file_name: str) -> str:
    if not file_name.endswith(".html"):
        file_name += ".html"

    return file_name


def get_html(file_name: str) -> str:
    file_path = get_path(ensure_html_file(f"data/{file_name}"))
    with open(file_path, "r") as fp:
        _html = (
            fp.read()
            .replace("\n", "")
            .replace("\t", "")
        )

    _html = re.sub(r"[ ]{2,}", " ", _html)
    return _html


def get_introduction_html() -> str:
    return get_html("introduction.html")


def get_data_table_html() -> str:
    return get_html("data_table.html")


def get_use_category_intro_html() -> str:
    return get_html("uc_intro.html")


def get_sunsetted_measures() -> SunsettedMeasuresSection:
    data = get_json("data/sunsetted_measures.json")
    return SunsettedMeasuresSection(data)
