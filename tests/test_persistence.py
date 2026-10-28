import os
import sys
import shutil
import tempfile
import logging
import errno
import stat
from unittest.mock import patch

import pytest

from msal_extensions.persistence import *


def _is_env_var_defined(env_var):
    return bool(  # (WTF) What-The-Finding:
    # The bool(...) is necessary, otherwise skipif(...) would treat "true" as
    # string conditions and then raise an undefined "true" exception.
    # https://docs.pytest.org/en/latest/historical-notes.html#string-conditions
        os.getenv(env_var))


# Note: If you use tox, remember to pass them through via tox.ini
# https://tox.wiki/en/latest/example/basic.html#passing-down-environment-variables
is_running_on_github_ci = _is_env_var_defined("GITHUB_ACTIONS")

@pytest.fixture
def temp_location():
    test_folder = tempfile.mkdtemp(prefix="test_persistence_roundtrip")
    yield os.path.join(test_folder, 'persistence.bin')
    shutil.rmtree(test_folder, ignore_errors=True)

def _test_persistence_roundtrip(persistence):
    payload = 'arbitrary content'
    persistence.save(payload)
    assert persistence.load() == payload

def _test_nonexistent_persistence(persistence):
    with pytest.raises(PersistenceNotFound):
        persistence.load()
    with pytest.raises(PersistenceNotFound):
        persistence.time_last_modified()

def test_file_persistence(temp_location):
    _test_persistence_roundtrip(FilePersistence(temp_location))

def test_nonexistent_file_persistence(temp_location):
    _test_nonexistent_persistence(FilePersistence(temp_location))

@pytest.mark.skipif(os.name != "posix", reason="Requires POSIX file permissions")
@pytest.mark.parametrize("mode", [0o644, 0o666])
def test_file_persistence_restricts_existing_permissions(temp_location, mode):
    with open(temp_location, "w") as handle:
        handle.write("previous content")
    os.chmod(temp_location, mode)

    persistence = FilePersistence(temp_location)
    persistence.save("new")

    assert persistence.load() == "new"
    assert stat.S_IMODE(os.stat(temp_location).st_mode) == 0o600

@pytest.mark.skipif(os.name != "posix", reason="Requires POSIX file permissions")
def test_file_persistence_permission_failure_preserves_content(temp_location):
    with open(temp_location, "w") as handle:
        handle.write("previous content")
    os.chmod(temp_location, 0o644)
    persistence = FilePersistence(temp_location)

    with patch("msal_extensions.persistence.os.fchmod",
               side_effect=OSError(errno.EPERM, "Permission denied")) as chmod:
        with pytest.raises(OSError) as error:
            persistence.save("new secret")

    assert error.value.errno == errno.EPERM
    assert persistence.load() == "previous content"
    assert stat.S_IMODE(os.stat(temp_location).st_mode) == 0o644
    with pytest.raises(OSError) as closed:
        os.fstat(chmod.call_args[0][0])
    assert closed.value.errno == errno.EBADF

@pytest.mark.skipif(os.name != "posix", reason="Requires POSIX file permissions")
def test_file_persistence_touch_creates_private_marker(temp_location):
    persistence = FilePersistence(temp_location)
    previous_umask = os.umask(0o022)
    try:
        persistence.touch()
    finally:
        os.umask(previous_umask)

    assert persistence.load() == ""
    assert stat.S_IMODE(os.stat(temp_location).st_mode) == 0o600
    persistence.save("existing content")
    os.utime(temp_location, (1, 1))
    persistence.touch()
    assert persistence.load() == "existing content"
    assert persistence.time_last_modified() > 1

@pytest.mark.skipif(
    not sys.platform.startswith('win'),
    reason="Requires Windows Desktop")
def test_file_persistence_with_data_protection(temp_location):
    try:
        _test_persistence_roundtrip(FilePersistenceWithDataProtection(temp_location))
    except PersistenceDecryptionError:
        if is_running_on_github_ci:
            logging.warning("DPAPI tends to fail on Windows VM. Run this on your desktop to double check.")
        else:
            raise

@pytest.mark.skipif(
    not sys.platform.startswith('win'),
    reason="Requires Windows Desktop")
def test_nonexistent_file_persistence_with_data_protection(temp_location):
    _test_nonexistent_persistence(FilePersistenceWithDataProtection(temp_location))

@pytest.mark.skipif(
    not sys.platform.startswith('darwin'),
    reason="Requires OSX.")
def test_keychain_persistence(temp_location):
    _test_persistence_roundtrip(KeychainPersistence(temp_location))

@pytest.mark.skipif(
    not sys.platform.startswith('darwin'),
    reason="Requires OSX.")
def test_nonexistent_keychain_persistence(temp_location):
    random_service_name = random_account_name = str(id(temp_location))
    _test_nonexistent_persistence(
        KeychainPersistence(temp_location, random_service_name, random_account_name))

@pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason="Requires Linux Desktop. Headless or SSH session won't work.")
def test_libsecret_persistence(temp_location):
    _test_persistence_roundtrip(LibsecretPersistence(temp_location))

@pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason="Requires Linux Desktop. Headless or SSH session won't work.")
def test_nonexistent_libsecret_persistence(temp_location):
    random_schema_name = random_value = str(id(temp_location))
    _test_nonexistent_persistence(LibsecretPersistence(
        temp_location,
        random_schema_name,
        {"my_attr_1": random_value, "my_attr_2": random_value},
        ))
