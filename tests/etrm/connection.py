import re
import json
import unittest as ut

from src import utils, patterns
from src.etrm.models import (
    Measure
)
from src.etrm.connection import ETRMConnection
from src.etrm.exceptions import (
    ETRMResponseError,
    ETRMRequestError,
    UnauthorizedError
)
from tests.etrm import resources as etrm_resources


class ConnectionTestCase(ut.TestCase):
    def test_invalid_api_key(self) -> None:
        """Tests connection initialization with strings that do not
        follow the correct API key format.
        """

        with self.assertRaises(UnauthorizedError):
            ETRMConnection('fake api key')
            ETRMConnection('Token a3232j120d')
            ETRMConnection('daowkndnw')

    def assert_api_key(self, api_key: str) -> None:
        try:
            ETRMConnection(api_key)
        except UnauthorizedError:
            self.fail(f'API key [{api_key}] should be valid')

    def test_valid_api_key(self) -> None:
        """Tests connection initialization with strings that follow
        the correct API key format.
        """

        self.assert_api_key('Token ae1bd3910c12')
        self.assert_api_key('a02be28709edacbe')


class ETRMConnectionTester:
    def __init__(self, api_key: str, stage: bool=False):
        self.connection = ETRMConnection(api_key, stage)

    def get_measure(self, measure_id: str) -> Measure:
        file_path = etrm_resources.get_path(f'{measure_id.upper()}.json')
        with open(file_path, 'r') as fp:
            measure_json = json.load(fp)
        return Measure(measure_json)


class RequestTestCase(ut.TestCase, ETRMConnectionTester):
    def assert_measure(self, measure_id: str) -> None:
        json_measure = self.get_measure(measure_id)
        etrm_measure = self.connection.get_measure(measure_id)
        self.assertEqual(json_measure, etrm_measure)

    def test_get_measure(self) -> None:
        """Tests the `get_measure` method.
        
        Asserts that `Measure` objects are only returned when they
        should be and that the `Measure` objects are properly created.
        """

        self.assert_measure('SWFS017-03')
        self.assert_measure('SWFS019-03')

        with self.assertRaises(ETRMResponseError):
            self.connection.get_measure('fakeid')

        with self.assertRaises(ETRMRequestError):
            self.connection.get_measure('SWFS017/03/permutations')
            self.connection.get_measure('test invalid whitespace')

    def assert_measure_ids(self,
                           use_category: str | None=None,
                           loops: int=2
                          ) -> None:
        offset = 0
        limit = 25
        id_list: list[list[str]] = []
        count_list: list[int] = []
        for _ in range(len(loops)):
            ids, count = self.connection.get_measure_ids(offset,
                                                         limit,
                                                         use_category)
            id_list.append(ids)
            count_list.append(count)

        for i in range(1, len(count_list)):
            self.assertEqual(count_list[0], count_list[i])

        id_set: set[str] = {}
        for i in range(len(id_list)):
            for measure_id in id_list[i]:
                self.assertNotIn(measure_id, id_set)
                re_match = re.fullmatch(patterns.STWD_ID, measure_id)
                self.assertIsNotNone(re_match,
                                     f'invalid measure ID: {measure_id}')
                if use_category is not None:
                    self.assertEqual(use_category, re_match.group(3))
                id_set.add(measure_id)

    def test_get_measure_ids(self) -> None:
        """Tests the `get_measure_ids` method.

        Asserts that the method returns the proper measure IDs and that
        all request queries were properly applied.
        """

        self.assert_measure_ids()
        self.assert_measure_ids(use_category='FS')
        self.assert_measure_ids(use_category='HC')

    def assert_all_measure_ids(self, use_category: str | None=None) -> None:
        init_ids, count = self.connection.get_measure_ids(
            use_category=use_category
        )
        all_ids = self.connection.get_all_measure_ids(
            use_category=use_category
        )

        self.assertListEqual(init_ids, all_ids[0:len(init_ids)])
        self.assertEqual(count, len(all_ids))

    def test_get_all_measure_ids(self) -> None:
        """Tests the `get_all_measure_ids` method.
        
        Asserts that all measure were properly retrieved and that none
        are missing.
        """

        self.assert_all_measure_ids()
        self.assert_all_measure_ids(use_category='FS')
        self.assert_all_measure_ids(use_category='HC')

    def assert_measure_versions(self, statewide_id: str) -> None:
        versions = self.connection.get_measure_versions(statewide_id)
        for version in versions:
            re_match = re.fullmatch(patterns.VERSION_ID, version)
            self.assertIsNotNone(re_match)

    def test_get_measure_versions(self) -> None:
        """Tests the `get_measure_versions` method.
        
        Asserts that only valid statewide IDs can be used and that
        all returned measure versions are correct.
        """

        invalid_ids = [
            'SWFS017/03/..',
            'SWHC013/?offset=50',
            '#ref_id',
            'Hello there',
            'General Kenobi'
        ]
        for string in invalid_ids:
            with self.assertRaises(ETRMRequestError):
                self.connection.get_measure_versions(string)
    
        valid_ids = [
            'SWFS017',
            'SWHC014'
        ]
        for string in valid_ids:
            self.assert_measure_versions(string)

    def assert_permutation_costs(self,
                                 measure_id: str,
                                 expected_stnd: tuple[float, float, float],
                                 expected_prex: tuple[float, float, float],
                                 expected_inc: float,
                                 expected_tot: float
                                ) -> None:
        measure = self.connection.get_measure(measure_id)
        permutations = self.connection.get_permutations(measure)

        stnd_costs = permutations.get_standard_costs()
        self.assertTupleEqual(stnd_costs, expected_stnd)

        prex_costs = permutations.get_pre_existing_costs()
        self.assertTupleEqual(prex_costs, expected_prex)

        inc_cost = permutations.get_incremental_cost()
        self.assertEqual(inc_cost, expected_inc)

        tot_cost = permutations.get_total_cost()
        self.assertEqual(tot_cost, expected_tot)

    def test_permutation_costs(self) -> None:
        """Tests permutation cost calculation methods."""

        # MAT - NC / AOE
        self.assert_permutation_costs('SWFS012-03',
                                      (0.591, 2890, 121.025),
                                      (0.591, 2890, 121.025),
                                      917.49,
                                      1942.44)


class UserTestCase(RequestTestCase):
    def setUp(self) -> None:
        api_key = utils.get_api_key(role='user')
        ETRMConnectionTester.__init__(self, api_key)


class AdminTestCase(RequestTestCase):
    def setUp(self) -> None:
        api_key = utils.get_api_key(role='admin')
        ETRMConnectionTester.__init__(self, api_key)


def suite() -> ut.TestSuite:
    suite = ut.TestSuite()
    suite.addTests(
        [
            ConnectionTestCase('test_valid_api_key'),
            ConnectionTestCase('test_invalid_api_key')
        ]
    )

    request_test_methods = [
        func
        for func
        in dir(RequestTestCase)
        if (
            callable(getattr(RequestTestCase, func))
                and func.startswith('test_')
        )
    ]
    for method in request_test_methods:
        suite.addTest(UserTestCase(method))
        # suite.addTest(AdminTestCase(method))

    return suite


if __name__ == '__main__':
    runner = ut.TextTestRunner()
    runner.run(suite())
