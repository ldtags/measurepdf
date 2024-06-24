import unicodedata
from typing import Any

from src.exceptions import ETRMResponseError
from src.utils import getc


ETRM_URL = 'https://www.caetrm.com'


class MeasureInfo:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.url = getc(res_json, 'url', str)
        except IndexError:
            raise ETRMResponseError()


class MeasuresResponse:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.count = getc(res_json, 'count', int)
            self.next = getc(res_json, 'next', str)
            self.previous = getc(res_json, 'previous', str)
            self.results = getc(res_json, 'results', list[MeasureInfo])
        except IndexError:
            raise ETRMResponseError()


class MeasureVersionInfo:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.version = getc(res_json, 'version', str)
            self.status = getc(res_json, 'status', str)
            self.change_description = getc(res_json, 'change_description', str)
            self.owner = getc(res_json, 'owner', str)
            self.is_published = getc(res_json, 'is_published', str)
            self.date_committed = getc(res_json, 'date_committed', str)
            self.url = getc(res_json, 'url', str)
        except IndexError:
            raise ETRMResponseError('malformed measure version info')


class MeasureVersionsResponse:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.statewide_measure_id = getc(res_json, 'statewide_measure_id', str)
            self.use_category = getc(res_json, 'use_category', str)
            self.versions = getc(res_json, 'versions', list[MeasureVersionInfo])
        except IndexError:
            raise ETRMResponseError('malformed measure versions response')


class Label:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.active = getc(res_json, 'active', str)
            self.description = getc(res_json, 'description', str)
        except IndexError:
            raise ETRMResponseError()


class Determinant:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.labels = getc(res_json, 'labels', list[Label])
            self.description = getc(res_json, 'description', str)
            self.order = getc(res_json, 'order', int)
            self.reference_refs = getc(res_json, 'reference_refs', list[str])
        except IndexError:
            raise ETRMResponseError()


class SharedDeterminant:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.order = getc(res_json, 'order', int)
            self.version = getc(res_json, 'version', dict[str, str])['version_string']
            self.active_labels = getc(res_json, 'active_labels', list[str])
            self.url = getc(res_json, 'url', str)
        except IndexError:
            raise ETRMResponseError()


class SharedValueTable:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.order = getc(res_json, 'order', int)
            self.version = getc(res_json, 'version', dict[str, str])['version_string']
            self.url = getc(res_json, 'url', str)
        except IndexError:
            raise ETRMResponseError()


class Column:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.unit = getc(res_json, 'unit', str)
            self.reference_refs = getc(res_json, 'reference_refs', list[str])
        except IndexError:
            raise ETRMResponseError()


class ValueTable:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.type = getc(res_json, 'type', str)
            self.description = getc(res_json, 'description', str)
            self.order = getc(res_json, 'order', int)
            self.determinants = getc(res_json, 'determinants', list[str])
            self.columns = getc(res_json, 'columns', list[Column])
            self.values = getc(res_json, 'values', list[list[str | None]])
            self.reference_refs = getc(res_json, 'reference_refs', list[str])
        except IndexError:
            raise ETRMResponseError()


class Calculation:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.order = getc(res_json, 'order', int)
            self.unit = getc(res_json, 'unit', str)
            self.determinants = getc(res_json, 'determinants', list[str])
            self.values = getc(res_json, 'values', list[list[str]])
            self.reference_refs = getc(res_json, 'reference_refs', list[str])
        except IndexError:
            raise ETRMResponseError()


class ExclusionTable:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.order = getc(res_json, 'order', int)
            self.determinants = getc(res_json, 'determinants', list[str])
            self.values = getc(res_json, 'values', list[tuple[str, str, bool]])
            self.reference_refs = getc(res_json, 'reference_refs', list[str])
        except IndexError:
            raise ETRMResponseError()


class Measure:
    __characterization_names = [
        'technology_summary',
        'measure_case_description',
        'base_case_description',
        'code_requirements',
        'program_requirements',
        'program_exclusions',
        'data_collection_requirements',
        'electric_savings',
        'peak_electric_demand_reduction',
        'gas_savings',
        'life_cycle',
        'base_case_material_cost',
        'measure_case_material_cost',
        'base_case_labor_cost',
        'measure_case_labor_cost',
        'net_to_gross',
        'gsia',
        'non_energy_impacts',
        'deer_differences_analysis'
    ]

    def __init__(self, res_json: dict[str, Any]):
        self._json = res_json
        try:
            self.statewide_measure_id = getc(res_json, 'statewide_measure_id', str)
            self.is_published = getc(res_json, 'is_published', bool)
            self.name = getc(res_json, 'name', str)
            self.use_category = getc(res_json, 'use_category', str)
            self.status = getc(res_json, 'status', str)
            self.effective_start_date = getc(res_json, 'effective_start_date', str)
            self.sunset_date = getc(res_json, 'sunset_date', str | None)
            self.pa_lead = getc(res_json, 'pa_lead', str)
            self.permutation_method = getc(res_json, 'permutation_method', int)
            self.workpaper_cover_sheet = getc(res_json, 'workpaper_cover_sheet', str)
            self.characterization_source_file = getc(res_json, 'characterization_source_file', str | None)
            self.determinants = getc(res_json, 'determinants', list[Determinant])
            self.shared_determinant_refs = getc(res_json, 'shared_determinant_refs', list[SharedDeterminant])
            self.shared_lookup_refs = getc(res_json, 'shared_lookup_refs', list[SharedValueTable])
            self.value_tables = getc(res_json, 'value_tables', list[ValueTable])
            self.calculations = getc(res_json, 'calculations', list[Calculation])
            self.exclusion_tables = getc(res_json, 'exclusion_tables', list[ExclusionTable])
            self.full_version_id = getc(res_json, 'full_version_id', str)
            self.date_committed = getc(res_json, 'date_committed', str)
            self.change_description = getc(res_json, 'change_description', str)
            self.owner = getc(res_json, 'owner', str)
            self.permutations_url = getc(res_json, 'permutations_url', str)
            self.property_data_url = getc(res_json, 'property_data_url', str)
            id_path = '/'.join(self.full_version_id.split('-'))
            self.link = f'{ETRM_URL}/measure/{id_path}'
        except IndexError:
            raise ETRMResponseError()

        self.characterizations = self.__get_characterizations()

    def __get_characterizations(self) -> dict[str, str]:
        char_list: dict[str, str] = {}
        for char_name in self.__characterization_names:
            try:
                uchar = self._json[char_name]
                char_list[char_name] = unicodedata.normalize('NFKD', uchar)
            except KeyError:
                raise ETRMResponseError()

        return char_list

    def get_determinant(self, name: str) -> Determinant | None:
        for determinant in self.determinants:
            if determinant.api_name == name or determinant.name == name:
                return determinant
        return None

    def get_shared_parameter(self, name: str) -> SharedDeterminant | None:
        for parameter in self.shared_determinant_refs:
            if parameter.version.split('-')[0] == name:
                return parameter
        return None

    def get_value_table(self, name: str) -> ValueTable | None:
        for table in self.value_tables:
            if table.name == name or table.api_name.lower() == name.lower():
                return table
        return None

    def get_table_data(self, name: str) -> list[list[str]] | None:
        table = self.get_value_table(name)
        if table is None:
            return None

        headers: list[str] = []
        for api_name in table.determinants:
            determinant = self.get_determinant(api_name)
            headers.append(determinant.name)
        for column in table.columns:
            headers.append(f'{column.name} ({column.unit})')

        body: list[list[str]] = []
        for row in table.values:
            table_row: list[str] = []
            for item in row:
                if item is None:
                    table_row.append('')
                else:
                    table_row.append(item)
            body.append(table_row)

        data = [headers]
        data.extend(body)
        return data


class Reference:
    def __init__(self, res_json: dict[str, Any]):
        self.json = res_json
        try:
            self.reference_code = getc(res_json, 'reference_code', str)
            self.reference_citation = getc(res_json, 'reference_citation', str)
            self.source_reference = getc(res_json, 'source_reference', str | None)
            self.source_url = getc(res_json, 'source_url', str | None)
            self.reference_location = getc(res_json, 'reference_location', str | None)
            self.reference_type = getc(res_json, 'reference_type', str)
            self.publication_title = getc(res_json, 'publication_title', str | None)
            self.lead_author = getc(res_json, 'lead_author', str | None)
            self.lead_author_org = getc(res_json, 'lead_author_org', str | None)
            self.sponsor_org = getc(res_json, 'sponsor_org', str | None)
            self.source_document = getc(res_json, 'source_document', str)
        except IndexError:
            raise ETRMResponseError()
