from __future__ import annotations
import math
import pandas as pd
import datetime as dt
import unicodedata
from typing import Any, overload
from pandas import DataFrame, Series

from src import utils
from src.etrm import constants as cnst
from src.etrm.exceptions import ETRMResponseError, ETRMConnectionError
from src.utils import getc


def convert_from_utc(date_string: str) -> dt.datetime:
    return dt.datetime.strptime(
        date_string,
        r"%Y-%m-%dT%H:%M:%S.%fZ"
    ).replace(
        tzinfo=dt.timezone.utc
    )


def is_nc_nr(row) -> bool:
    val = row[cnst.MAT]
    if not isinstance(val, str):
        return False

    return val == "NC" or val == "NR"


def is_ar(row) -> bool:
    val = row[cnst.MAT]
    if not isinstance(val, str):
        return False

    return val == "AR"


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

    def get_nc_nr_rows(self) -> DataFrame:
        return self.data.loc[self.data.apply(is_nc_nr, axis=1)]

    def get_ar_rows(self) -> DataFrame:
        return self.data.loc[self.data.apply(is_ar, axis=1)]

    def get_standard_savings(self, nc_nr_field: str, ar_field: str) -> float | None:
        """Returns the standard savings from the specified fields.

        Typically, an MAT is either NC/NR, AR, or other. When this is not the
        case (i.e., varying MATs), rows with NC/NR and AR MATs are averaged.
        Rows with other MATs are not included.
        """

        nc_nr_rows = self.get_nc_nr_rows()
        ar_rows = self.get_ar_rows()
        if nc_nr_rows.empty and ar_rows.empty:
            return None

        stnd_savings: Series = pd.concat(
            [nc_nr_rows[nc_nr_field], ar_rows[ar_field]],
            ignore_index=True,
            sort=False
        )

        val = stnd_savings.mean()
        if math.isnan(val):
            return 0.0

        return val

    def get_standard_pedr(self) -> float | None:
        return self.get_standard_savings(cnst.PEDR_1, cnst.PEDR_2)

    def get_standard_es(self) -> float | None:
        return self.get_standard_savings(cnst.ES_1, cnst.ES_2)

    def get_standard_gs(self) -> float | None:
        return self.get_standard_savings(cnst.GS_1, cnst.GS_2)

    def get_standard_ws(self) -> float | None:
        return self.get_standard_savings(cnst.WS_1, cnst.WS_2)

    def get_existing_savings(self, field: str) -> float | None:
        rows = self.data.loc[
            ~self.data[cnst.MAT].isin(["NC", "NR"])
        ]

        if rows.empty:
            return None

        val = rows[field].mean()
        if math.isnan(val):
            return 0

        return val

    def get_existing_pedr(self) -> float | None:
        return self.get_existing_savings(cnst.PEDR_1)

    def get_existing_es(self) -> float | None:
        return self.get_existing_savings(cnst.ES_1)

    def get_existing_gs(self) -> float | None:
        return self.get_existing_savings(cnst.GS_1)

    def get_existing_ws(self) -> float | None:
        return self.get_existing_savings(cnst.WS_1)

    def get_base_case_cost(self) -> float | None:
        nc_nr_rows = self.get_nc_nr_rows()
        ar_rows = self.get_ar_rows()
        other_rows = self.data.loc[
            self.data.apply(
                lambda row: not (is_nc_nr(row) or is_ar(row)),
                axis=1
            )
        ]

        all_costs: Series = pd.concat(
            [
                nc_nr_rows[cnst.ULC_1] + nc_nr_rows[cnst.UMC_1],
                ar_rows[cnst.ULC_2] + ar_rows[cnst.UMC_2],
                Series([0.0] * other_rows.size)
            ],
            ignore_index=True,
            sort=False
        )

        if all_costs.empty:
            return None

        avg_cost = all_costs.mean()
        if math.isnan(avg_cost):
            return 0.0

        return avg_cost

    def get_measure_cost(self) -> float | None:
        nc_nr_rows = self.get_nc_nr_rows()
        other_rows = self.data.loc[
            self.data.apply(
                lambda row: not is_nc_nr(row),
                axis=1
            )
        ]

        all_costs: Series = pd.concat(
            [
                nc_nr_rows[cnst.ULC_M] + nc_nr_rows[cnst.UMC_M],
                other_rows[cnst.MTC_1]
            ],
            ignore_index=True,
            sort=False
        )

        if all_costs.empty:
            return None

        avg_cost = all_costs.mean()
        if math.isnan(avg_cost):
            return 0.0

        return avg_cost

    def get_incremental_cost(self) -> float | None:
        nc_nr_rows = self.get_nc_nr_rows()
        ar_rows = self.get_ar_rows()
        other_rows = self.data.loc[
            self.data.apply(
                lambda row: not (is_nc_nr(row) or is_ar(row)),
                axis=1
            )
        ]

        all_costs: Series = pd.concat(
            [
                nc_nr_rows[cnst.MTC_1],
                ar_rows[cnst.MTC_2],
                Series([0.0] * other_rows.size)
            ],
            ignore_index=True,
            sort=False
        )

        if all_costs.empty:
            return None

        val = all_costs.mean()
        if math.isnan(val):
            return 0.0

        return val

    def get_eul_years(self, no_aoe: bool = True) -> float | None:
        if no_aoe:
            df = self.data.loc[
                ~self.data[cnst.MAT].eq("AOE")
            ]
        else:
            df = self.data

        if df.empty:
            return None

        val = df[cnst.EUL].mean()
        if math.isnan(val):
            return 0.0

        return val

    def get_rul_years(self) -> float | None:
        eul_yrs = self.data.loc[
            self.data[cnst.MAT].eq("AOE")
        ][cnst.EUL]

        rul_yrs = self.data.loc[
            self.data[cnst.MAT].eq("AR")
        ][cnst.RUL]

        if eul_yrs.empty and rul_yrs.empty:
            return None

        val = (eul_yrs + rul_yrs).mean()
        if math.isnan(val):
            return 0.0

        return val

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

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "api_name": self.api_name,
            "unit": self.unit,
            "reference_refs": self.reference_refs
        }


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

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "api_name": self.api_name,
            "parameters": self.parameters,
            "columns": [col.as_dict() for col in self.columns],
            "values": self.values,
            "references": self.references,
            "version": self.version,
            "status": self.status,
            "change_description": self.change_description,
            "owner": self.owner,
            "is_published": self.is_published,
            "committed_date": self.committed_date,
            "last_updated_date": self.last_updated_date,
            "type": self.type,
            "versions_url": self.versions_url,
            "url": self.url
        }


class SharedParameterVersion:
    def __init__(self, res_json: dict[str, Any]) -> None:
        self.type = getc(res_json, "type", str)
        self.version = getc(res_json, "version", str)
        self.versions_url = getc(res_json, "versions_url", str)
        self.url = getc(res_json, "url", str)
        committed_date = getc(res_json, "committed_date", str, None)
        if committed_date != "None":
            self.committed_date = convert_from_utc(committed_date)
        else:
            self.committed_date = None

        last_updated_date = getc(res_json, "last_updated_date", str, None)
        if last_updated_date != "None":
            self.last_updated_date = convert_from_utc(last_updated_date)
        else:
            self.last_updated_date = None

        try:
            _, version_num = self.version.split("-", 1)
            version_num = int(version_num)
        except ValueError:
            version_num = -1

        self.version_num = version_num


class SharedParameterLabel:
    def __init__(self, res_json: dict[str, Any]) -> None:
        self.name = getc(res_json, "name", str)
        self.api_name = getc(res_json, "api_name", str)
        self.description = getc(res_json, "description", str)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "api_name": self.api_name,
            "description": self.description
        }


class SharedParameter(SharedParameterVersion):
    def __init__(self, res_json: dict[str, Any]) -> None:
        super().__init__(res_json)
        self.name = getc(res_json, "name", str)
        self.api_name = getc(res_json, "api_name", str)
        self.labels = getc(res_json, "labels", list[SharedParameterLabel])
        self.description = getc(res_json, "description", str)
        self.references = getc(res_json, "references", list[str])
        self.version = getc(res_json, "version", str)
        self.status = getc(res_json, "status", str)
        self.change_description = getc(res_json, "change_description", str)
        self.owner = getc(res_json, "owner", str)
        self.is_published = getc(res_json, "is_published", bool)
        self._label_dict = {
            label.name: label
                for label
                in self.labels
        }

    def get_label(self, label: str) -> SharedParameterLabel | None:
        return self._label_dict.get(label)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "api_name": self.api_name,
            "labels": [label.as_dict() for label in self.labels],
            "description": self.description,
            "references": self.references,
            "version": self.version,
            "status": self.status,
            "change_description": self.change_description,
            "owner": self.owner,
            "is_published": self.is_published
        }


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
            self.link = f'{cnst.ETRM_URL}/measure/{id_path}'
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
    def start_date(self) -> dt.date:
        return utils.to_date(self.effective_start_date)

    @property
    def end_date(self) -> dt.date | None:
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
