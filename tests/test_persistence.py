import os
import sys
import shutil
import tempfile
import logging

import pytest

from msal_extensions.persistence import *


is_running_on_travis_ci = bool(  # (WTF) What-The-Finding:
    # The bool(...) is necessary, otherwise skipif(...) would treat "true" as
    # string conditions and then raise an undefined "true" exception.
    # https://docs.pytest.org/en/latest/historical-notes.html#string-conditions
    os.getenv("TRAVIS"))

@pytest.fixture
def temp_location():
    test_folder = tempfile.mkdtemp(prefix="test_persistence_roundtrip")
    yield os.path.join(test_folder, 'persistence.bin')
    shutil.rmtree(test_folder, ignore_errors=True)

def _test_persistence_roundtrip(persistence):
    payload = 'arbitrary content'
    persistence.save(payload)
    assert persistence.load() == payload

def test_file_persistence(temp_location):
    _test_persistence_roundtrip(FilePersistence(temp_location))

@pytest.mark.skipif(
    is_running_on_travis_ci or not sys.platform.startswith('win'),
    reason="Requires Windows Desktop")
def test_file_persistence_with_data_protection(temp_location):
    _test_persistence_roundtrip(FilePersistenceWithDataProtection(temp_location))

@pytest.mark.skipif(
    not sys.platform.startswith('darwin'),
    reason="Requires OSX. Whether running on TRAVIS CI does not seem to matter.")
def test_keychain_persistence(temp_location):
    _test_persistence_roundtrip(KeychainPersistence(
        temp_location, "my_service_name", "my_account_name"))

@pytest.mark.skipif(
    is_running_on_travis_ci or not sys.platform.startswith('linux'),
    reason="Requires Linux Desktop. Headless or SSH session won't work.")
def test_libsecret_persistence(temp_location):
    _test_persistence_roundtrip(LibsecretPersistence(
        temp_location,
        "my_schema_name",
        {"my_attr_1": "foo", "my_attr_2": "bar"},
        ))
