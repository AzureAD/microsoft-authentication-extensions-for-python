import pytest
from msal_extensions import CrossPlatLock


def test_ensure_file_deleted():
    lockfile = './test_lock_1.txt'

    try:
        FileNotFoundError
    except NameError:
        FileNotFoundError = IOError

    print("Testing with {}".format(CrossPlatLock))
    with CrossPlatLock(lockfile):
        pass

    with pytest.raises(FileNotFoundError):
        with open(lockfile):
            pass
