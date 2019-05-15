import pytest
from msal_extensions.cache_lock import CrossPlatLock


def test_ensure_file_deleted():
    lockfile = './test_lock_1.txt'

    try:
        FileNotFoundError
    except NameError:
        FileNotFoundError = IOError

    with CrossPlatLock(lockfile):
        pass

    with pytest.raises(FileNotFoundError):
        with open(lockfile):
            pass
