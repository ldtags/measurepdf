import os
import unittest as ut

from src import utils, asset_path, _ROOT


class MiscTestCase(ut.TestCase):
    def test_get_tkimage(self):
        valid_names = [
            'folder.png',
            'plus.png',
            'reset.png',
            'search.png'
        ]
        for file_name in valid_names:
            self.assertIsNotNone(utils.get_tkimage(file_name))

        invalid_names = [
            'dnoweidawod.awndoiawd'
        ]
        for file_name in invalid_names:
            with self.assertRaises(FileNotFoundError):
                utils.get_tkimage(file_name)

    def test_asset_path(self):
        asset_dir = os.path.join(_ROOT, 'assets')
        file_names = ['folder.png',
                      'plus.png',
                      'reset.png',
                      'search.png',
                      'etrm.ico']
        for file_name in file_names:
            valid_path = os.path.join(asset_dir, file_name)
            file_path = asset_path(file_name)
            self.assertEqual(valid_path, file_path)

        fake_names = ['folder.ico',
                      'plus.ico',
                      'pokempon.png',
                      'deaowidmalmwdk.dwwd']
        for file_name in fake_names:
            with self.assertRaises(FileNotFoundError):
                asset_path(file_name)


def suite() -> ut.TestSuite:
    suite = ut.TestSuite()
    suite.addTests(
        [
            MiscTestCase('test_get_tkimage'),
            MiscTestCase('test_asset_path')
        ]
    )
    return suite


if __name__ == '__main__':
    runner = ut.TextTestRunner()
    runner.run(suite())
