import unicodedata
from typing import Any

from src.utils import getc
from src.exceptions import ETRMResponseError


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
            self.statewide_measure_id = getc(res_json,
                                             'statewide_measure_id',
                                             str)
            self.use_category = getc(res_json, 'use_category', str)
            self.versions = getc(res_json,
                                 'versions',
                                 list[MeasureVersionInfo])
        except IndexError:
            raise ETRMResponseError('malformed measure versions response')


class Version:
    def __init__(self, res_json: dict[str, Any]):
        try:
            version_string = getc(res_json, 'version_string', str)
        except IndexError:
            raise ETRMResponseError()
        try:
            self.table_name, self.version = version_string.split('-', 1)
        except ValueError:
            raise ETRMResponseError(f'{version_string} is not'
                                    ' properly formatted')


class SharedDeterminantRef:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.order = getc(res_json, 'order', int)
            _version = getc(res_json, 'version', Version)
            self.name = _version.table_name
            self.version = _version.version
            self.active_labels = getc(res_json, 'active_labels', list[str])
            self.url = getc(res_json, 'url', str)
        except IndexError:
            raise ETRMResponseError()


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


class SharedLookupRef:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.order = getc(res_json, 'order', int)
            _version = getc(res_json, 'version', Version)
            self.name = _version.table_name
            self.version = _version.version
            self.url = getc(res_json, 'url', str)
        except IndexError:
            raise ETRMResponseError()


class Column:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.unit = getc(res_json, 'unit', str)
            try:
                self.reference_refs = getc(res_json,
                                           'reference_refs',
                                           list[str])
            except TypeError:
                self.reference_refs = getc(res_json, 'references', list[str])
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


class SharedValueTable:
    def __init__(self, res_json: dict[str, Any]):
        self.json = res_json
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.parameters = getc(res_json, 'parameters', list[str])
            self.columns = getc(res_json, 'columns', list[Column])
            self.values = getc(res_json,
                               'values',
                               list[list[str | float | None]])
            self.references = getc(res_json, 'references', list[str])
            self.version = getc(res_json, 'version', str)
            self.status = getc(res_json, 'status', str)
            self.change_description = getc(res_json, 'change_description', str)
            self.owner = getc(res_json, 'owner', str)
            self.is_published = getc(res_json, 'is_published', bool)
            self.committed_date = getc(res_json, 'committed_date', str)
            self.last_updated_date = getc(res_json, 'last_updated_date', str)
            self.type = getc(res_json, 'type', str)
            self.versions_url = getc(res_json, 'versions_url', str)
            self.url = getc(res_json, 'url', str)

            headers = [
                *self.parameters,
                *[col.api_name for col in self.columns]
            ]

            self.data: dict[str, dict[str, str | float | None]] = {}
            for row in self.values:
                self.data[row[0]] = {}
                for i, item in enumerate(row[1:], 1):
                    self.data[row[0]][headers[i]] = item

        except IndexError:
            raise ETRMResponseError()

    def __getitem__(self, description: str) -> dict[str, str | float | None]:
        return self.data[description]


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
            self.statewide_measure_id = getc(res_json,
                                             'statewide_measure_id',
                                             str)
            self.is_published = getc(res_json, 'is_published', bool)
            self.name = getc(res_json, 'name', str)
            self.use_category = getc(res_json, 'use_category', str)
            self.status = getc(res_json, 'status', str)
            self.effective_start_date = getc(res_json,
                                             'effective_start_date',
                                             str)
            self.sunset_date = getc(res_json, 'sunset_date', str | None)
            self.pa_lead = getc(res_json, 'pa_lead', str)
            self.permutation_method = getc(res_json, 'permutation_method', int)
            self.workpaper_cover_sheet = getc(res_json,
                                              'workpaper_cover_sheet',
                                              str)
            self.characterization_source_file \
                = getc(res_json, 'characterization_source_file', str | None)
            self.determinants = getc(res_json,
                                     'determinants',
                                     list[Determinant])
            self.shared_determinant_refs = getc(res_json,
                                                'shared_determinant_refs',
                                                list[SharedDeterminantRef])
            self.shared_lookup_refs = getc(res_json,
                                           'shared_lookup_refs',
                                           list[SharedLookupRef])
            self.value_tables = getc(res_json,
                                     'value_tables',
                                     list[ValueTable])
            self.calculations = getc(res_json,
                                     'calculations',
                                     list[Calculation])
            self.exclusion_tables = getc(res_json,
                                         'exclusion_tables',
                                         list[ExclusionTable])
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
            if (determinant.api_name.lower() == name.lower()
                    or determinant.name.lower() == name.lower()):
                return determinant
        return None

    def get_shared_parameter(self, name: str) -> SharedDeterminantRef | None:
        for parameter in self.shared_determinant_refs:
            if parameter.name.lower() == name.lower():
                return parameter
        return None

    def get_value_table(self, name: str) -> ValueTable | None:
        for table in self.value_tables:
            if (table.name.lower() == name.lower()
                    or table.api_name.lower() == name.lower()):
                return table
        return None

    def get_shared_lookup(self, name: str) -> SharedLookupRef | None:
        for lookup_ref in self.shared_lookup_refs:
            if lookup_ref.name.lower() == name.lower():
                return lookup_ref
        return None


class Reference:
    def __init__(self, res_json: dict[str, Any]):
        self.json = res_json
        try:
            self.reference_code = getc(res_json, 'reference_code', str)
            self.reference_citation = getc(res_json, 'reference_citation', str)
            self.source_reference = getc(res_json,
                                         'source_reference',
                                         str | None)
            self.source_url = getc(res_json, 'source_url', str | None)
            self.reference_location = getc(res_json,
                                           'reference_location',
                                           str | None)
            self.reference_type = getc(res_json, 'reference_type', str)
            self.publication_title = getc(res_json,
                                          'publication_title',
                                          str | None)
            self.lead_author = getc(res_json, 'lead_author', str | None)
            self.lead_author_org = getc(res_json,
                                        'lead_author_org',
                                        str | None)
            self.sponsor_org = getc(res_json, 'sponsor_org', str | None)
            self.source_document = getc(res_json, 'source_document', str)
        except IndexError:
            raise ETRMResponseError()
