import os
import sys

from tests.context import utils, asset_path


def test_utils():
    assert utils.get_tkimage('folder.png') is not None
    assert utils.get_tkimage('plus.png') is not None
    assert utils.get_tkimage('reset.png') is not None
    assert utils.get_tkimage('search.png') is not None
    print('Passed valid get_tkimage tests', file=sys.stderr)

    try:
        fake_name = 'dnoweidawod.awndoiawd'
        utils.get_tkimage(fake_name)
        raise AssertionError('get_tkimage() did not throw FileNotFoundError'
                             f' for {fake_name}')
    except FileNotFoundError:
        pass
    print('Passed invvalid get_tkimage tests', file=sys.stderr)


def test_init_utils():
    asset_dir = os.path.join('C:',
                             'Users',
                             'Liam Tangney',
                             'Programs',
                             'Python',
                             'MeasureSummary',
                             'src',
                             'assets')
    file_names = ['folder.png',
                  'plus.png',
                  'reset.png',
                  'search.png',
                  'etrm.ico']
    for file_name in file_names:
        assert asset_path(file_name, 'images') == os.path.join(asset_dir,
                                                               file_name)
    print('Passed valid assert_path tests', file=sys.stderr)

    fake_names = ['folder.ico',
                  'plus.ico',
                  'pokempon.png',
                  'deaowidmalmwdk.dwwd']
    for file_name in fake_names:
        try:
            assert asset_path(file_name, 'images') == os.path.join(asset_dir,
                                                                   file_name)
            raise AssertionError(f'{file_name} should have thrown a'
                                 '  FileNotFoundError')
        except FileNotFoundError:
            pass
    print('Passed invalid assert_path tests', file=sys.stderr)


def main():
    test_utils()
    test_init_utils()


if __name__ == '__main__':
    main()
