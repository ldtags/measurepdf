from typing import Any

from src.utils import JSONObject, convert_from_utc


class Revision(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.version = self.get("version", float)
        self.publish_date = convert_from_utc(self.get("publish_date", str))
        self.description = self.get("description", str)
        self.owner = self.get("owner", str)


class KeyTerminology(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.name = self.get("name", str)
        self.api_name = self.get("api_name", str | None)
        self.content = self.get("content", str)
        self.contains_table = self.get("contains_table", bool)
        self.columns = self.get("columns", list[str] | None)
        self.column_mappings = self.get("column_mappings", dict[str, str] | None)
        self.data = self.get("data", list[list[str]] | None)
        self.append = self.get("append", str | None)
        self.sub_sections = self.get("sub_sections", list[KeyTerminology] | None)
        self.row_split = self.get("row_split", int | None, None)
        self.caption = self.get("caption", str | None, None)

        for i, section in enumerate(self.sub_sections or []):
            self.sub_sections[i] = KeyTerminology(section)

    def requires_etrm_table(self) -> bool:
        if self.api_name is None:
            return False

        if self.columns is None:
            return False

        if self.data is not None and self.append is None:
            return False

        return True

    def get_table_headers(self) -> list[str] | None:
        if self.columns is None:
            return None

        headers = self.columns.copy()
        if self.column_mappings is None:
            return headers

        for i, header in enumerate(headers):
            mapping = self.column_mappings.get(header)
            if mapping is not None:
                headers[i] = mapping

        return headers


class KeyTerminologySection(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.introduction = self.get("introduction", str)
        items = self.get("parameters", list[dict])
        self.items: list[KeyTerminology] = []
        for item in items:
            self.items.append(KeyTerminology(item))


class SectionDescription(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.offering_id = self.get("Offering ID", str)
        self.base_case = self.get("Base Case Description", str)
        self.program_exclusion = self.get("Other: Program Exclusion / /", str)
        self.quality_assurance = self.get("Quality Assurance", str)
        self.important_notes = self.get("Important Notes", str)


class SunsettedMeasure(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.version_id = self.get("version_id", str)
        self.name = self.get("name", str)
        self.active_life = self.get("active_life", str)
        self.trm_update = self.get("trm_update", bool)
        self.version_update = self.get("version_update", bool)
        self.is_sunsetted = self.get("is_sunsetted", bool)


class SunsettedMeasureCollection(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.name = self.get("use_category", str)
        self.measures: list[SunsettedMeasure] = []
        for measure in self.get("measures", list[dict]):
            self.measures.append(SunsettedMeasure(measure))


class SunsettedMeasuresSection(JSONObject):
    def __init__(self, _json: str | dict[str, Any]) -> None:
        super().__init__(_json)
        self.introduction = self.get("introduction", str)
        self.use_categories: list[SunsettedMeasureCollection] = []
        for use_category in self.get("use_categories", list[dict]):
            self.use_categories.append(SunsettedMeasureCollection(use_category))
