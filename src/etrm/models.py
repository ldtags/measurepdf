from __future__ import annotations
import math
import pandas as pd
import datetime
import unicodedata
from enum import Enum
from typing import Any, overload
from pandas import DataFrame, Series

from src import utils
from src.utils import getc
from src.etrm.exceptions import ETRMResponseError, ETRMConnectionError


ETRM_URL = 'https://www.caetrm.com'


class Baseline(Enum):
    PEDR_1 = 'UnitkW1stBaseline'
    """First Baseline - Peak Electric Demand Reduction"""

    PEDR_2 = 'UnitkW2ndBaseline'
    """Second Baseline - Peak Electric Demand Reduction"""

    ES_1 = 'UnitkWh1stBaseline'
    """First Baseline - Electric Savings"""

    ES_2 = 'UnitkWh2ndBaseline'
    """Second Baseline - Electric Savings"""

    GS_1 = 'UnitTherm1stBaseline'
    """First Baseline - Gas Savings"""

    GS_2 = 'UnitTherm2ndBaseline'
    """Second Baseline - Gas Savings"""

    MTC_1 = 'UnitMeaCost1stBaseline'
    """Measure Total Cost 1st Baseline"""

    MTC_2 = 'UnitMeaCost2ndBaseline'
    """Measure Total Cost 2nd Baseline"""


class PermutationsTable:
    def __init__(self, res_json: dict[str, Any]):
        self.json = res_json
        try:
            self.count = getc(res_json, 'count', int)
            self.links = getc(res_json, 'links', self._Links)
            self.headers = getc(res_json, 'headers', list[str])
            self.results = getc(res_json, 'results', list[list[str | float | None]])

            self.data = DataFrame(
                data=self.results,
                columns=self.headers
            )

            columns = [list(col) for col in zip(*self.results)]
            data: dict[str, list[str | float | None]] = {}
            for x, header in enumerate(self.headers):
                data[header] = columns[x]
            self.data = DataFrame(data)

        except IndexError:
            raise ETRMResponseError()

    class _Links:
        def __init__(self, links: dict[str, str | None]):
            self.next = links.get('next', None)
            self.previous = links.get('previous', None)

    def __getitem__(self, header: str) -> Series:
        try:
            return self.data[header]
        except KeyError as err:
            raise ETRMConnectionError(
                f'Permutation column {header} not found'
            ) from err

    def join(self, table: PermutationsTable) -> None:
        if table.count == 0:
            return

        if self.headers != table.headers:
            raise ETRMResponseError()

        self.results.extend(table.results)

    def average(self, column_name: str) -> float | None:
        column = self.data.get(column_name, None)
        if column == None:
            return None

        if not all([type(item) is float for item in column]):
            return None

        return sum(column) / len(column)

    def get_standard_costs(self) -> tuple[float, float, float]:
        """Returns a three-tuple of the (Peak Electric Demand Reduction,
         Electric Savings, Gas Savings) standard costs.

        The standard costs are either:
            First Baseline  (NC or NR)
            Second Baseline (AR)
            None            (other)
        """

        baseline_count = 0
        pedr = 0.0
        es = 0.0
        gs = 0.0

        nc_nr_rows = self.data.loc[
            self.data['MeasAppType'].isin(['NC', 'NR'])
        ]
        if not nc_nr_rows.empty:
            pedr += nc_nr_rows[Baseline.PEDR_1.value].mean()
            es += nc_nr_rows[Baseline.ES_1.value].mean()
            gs += nc_nr_rows[Baseline.GS_1.value].mean()
            baseline_count += 1

        ar_rows = self.data.loc[
            self.data['MeasAppType'] == 'AR'
        ]
        if not ar_rows.empty:
            pedr += ar_rows[Baseline.PEDR_2.value].mean()
            es += ar_rows[Baseline.ES_2.value].mean()
            gs += ar_rows[Baseline.GS_2.value].mean()
            baseline_count += 1

        if baseline_count == 0:
            return (0.0, 0.0, 0.0)

        if math.isnan(pedr):
            pedr = 0.0
        else:
            pedr /= baseline_count

        if math.isnan(es):
            es = 0.0
        else:
            es /= baseline_count

        if math.isnan(gs):
            gs = 0.0
        else:
            gs /= baseline_count

        return (pedr, es, gs)

    def get_pre_existing_costs(self) -> tuple[float, float, float]:
        """Returns a three-tuple of the (Peak Electric Demand Reduction,
         Electric Savings, Gas Savings) pre-existing costs.

        The pre-existing costs are either:
            None            (NC or NR)
            First Baseline  (other)
        """

        rows = self.data.loc[
            ~self.data['MeasAppType'].isin(['NC', 'NR'])
        ]

        pedr = rows[Baseline.PEDR_1.value].mean()
        if math.isnan(pedr):
            pedr = 0.0

        es = rows[Baseline.ES_1.value].mean()
        if math.isnan(es):
            es = 0.0

        gs = rows[Baseline.GS_1.value].mean()
        if math.isnan(gs):
            gs = 0.0
        return (pedr, es, gs)

    def get_incremental_cost(self) -> float:
        """Returns the incremental cost of the measure.
        
        The incremental cost is either:
            Measure Total Cost 1st Baseline (NC or NR)
            Measure Total Cost 2nd Baseline (AR)
            None                            (other)
        """

        mtc_1_col = self.data.loc[
            self.data['MeasAppType'].isin(['NC', 'NR'])
        ][Baseline.MTC_1.value]

        mtc_2_col = self.data.loc[
            self.data['MeasAppType'] == 'AR'
        ][Baseline.MTC_2.value]

        if mtc_1_col.empty and mtc_2_col.empty:
            return 0.0

        if mtc_1_col.empty:
            mtc = mtc_2_col.mean()
        elif mtc_2_col.empty:
            mtc = mtc_1_col.mean()
        else:
            mtc_col = pd.concat([mtc_1_col, mtc_2_col],
                                ignore_index=True,
                                sort=False)
            mtc = mtc_col.mean()

        if math.isnan(mtc):
            return 0.0
        return mtc

    def get_total_cost(self) -> float:
        """Returns the total cost of the measure.
        
        The total cost is either:
            None                            (NC or NR)
            Measure Total Cost 1st Baseline (other)
        """

        mtc_col = self.data.loc[
            ~self.data['MeasAppType'].isin(['NC', 'NR'])
        ][Baseline.MTC_1.value]
        mtc = mtc_col.mean()
        if math.isnan(mtc):
            mtc = 0.0
        return mtc

    def __eq__(self, other) -> bool:
        if not isinstance(other, PermutationsTable):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class MeasureInfo:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.url = getc(res_json, 'url', str)
        except IndexError:
            raise ETRMResponseError()

    def __eq__(self, other) -> bool:
        if not isinstance(other, MeasureInfo):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class MeasuresResponse:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.count = getc(res_json, 'count', int)
            self.next = getc(res_json, 'next', str)
            self.previous = getc(res_json, 'previous', str)
            self.results = getc(res_json, 'results', list[MeasureInfo])
        except IndexError:
            raise ETRMResponseError()

    def __eq__(self, other) -> bool:
        if not isinstance(other, MeasuresResponse):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, MeasureVersionInfo):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, MeasureVersionsResponse):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, Version):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, SharedDeterminantRef):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


class Label:
    def __init__(self, res_json: dict[str, Any]):
        try:
            self.name = getc(res_json, 'name', str)
            self.api_name = getc(res_json, 'api_name', str)
            self.active = getc(res_json, 'active', str)
            self.description = getc(res_json, 'description', str)
        except IndexError:
            raise ETRMResponseError()

    def __eq__(self, other) -> bool:
        if not isinstance(other, Label):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, Determinant):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, SharedLookupRef):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, Column):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, ValueTable):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

            self.data: dict[str, dict[str, list[str | float | None]]] = {}
            for row in self.values:
                eul_id = str(row[0])
                id_map = self.data.get(eul_id, {})
                for i, item in enumerate(row[1:], 1):
                    mapped_list = id_map.get(headers[i], [])
                    mapped_list.append(item)
                    id_map[headers[i]] = mapped_list
                self.data[eul_id] = id_map

        except IndexError:
            raise ETRMResponseError()

    def __eq__(self, other) -> bool:
        if not isinstance(other, SharedValueTable):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, Calculation):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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

    def __eq__(self, other) -> bool:
        if not isinstance(other, ExclusionTable):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)


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
        self.value_table_cache: dict[str, ValueTable] = {}

    def __eq__(self, other) -> bool:
        if not isinstance(other, Measure):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    @property
    def start_date(self) -> datetime.date:
        return utils.to_date(self.effective_start_date)

    @property
    def end_date(self) -> datetime.date | None:
        if self.sunset_date is None:
            return None

        return utils.to_date(self.sunset_date)

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

    def __get_value_table(self, name: str) -> ValueTable | None:
        table = self.value_table_cache.get(name, None)
        if table is not None:
            return table

        for table in self.value_tables:
            if (table.name.lower() == name.lower()
                    or table.api_name.lower() == name.lower()):
                return table
        return None
    
    @overload
    def get_value_table(self, name: str) -> ValueTable | None:
        ...

    @overload
    def get_value_table(self, *names: str) -> ValueTable | None:
        ...

    def get_value_table(self, *names: str) -> ValueTable | None:
        value_table: ValueTable | None = None
        for name in names:
            value_table = self.__get_value_table(name)
            if value_table != None:
                break
        return value_table

    def get_shared_lookup(self, name: str) -> SharedLookupRef | None:
        for lookup_ref in self.shared_lookup_refs:
            if lookup_ref.name.lower() == name.lower():
                return lookup_ref
        return None

    @staticmethod
    def sorting_key(measure: Measure) -> int:
        return utils.version_key(measure.full_version_id)
            

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

    def __eq__(self, other) -> bool:
        if not isinstance(other, Reference):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
