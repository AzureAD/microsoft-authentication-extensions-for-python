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

@pytest.mark.skipif(
    is_running_on_travis_ci, reason="Requires manual testing")
def test_windows_empty_file_exists_before_first_use():
    test_folder = tempfile.mkdtemp(prefix="msal_extension_test_windows_token_cache_roundtrip")
    cache_file = os.path.join(test_folder, 'msal.cache')
    open("msal.cache", 'w+')
    try:
        persistence = FilePersistenceWithDataProtection(cache_file)
        assert persistence.load() is None  # Empty file should just be a NO-OP
    finally:
        shutil.rmtree(test_folder, ignore_errors=True)

@pytest.mark.skipif(
    is_running_on_travis_ci, reason="Requires manual testing")
def test_windows_file_contains_data_before_first_use():
    test_folder = tempfile.mkdtemp(prefix="msal_extension_test_windows_token_cache_roundtrip")
    cache_file = os.path.join(test_folder, 'msal.cache')
    fh = open(cache_file, 'w+')
    cache_content = '{"AccessToken": {}, "Account": {}, "IdToken": {}, "RefreshToken": {}, "AppMetadata": {}}'
    fh.write(cache_content)
    fh.close()
    try:
        persistence = FilePersistenceWithDataProtection(cache_file)
        with pytest.raises(OSError) as err:
            persistence.load()
        assert err.value.winerror == 13  # WinError 13 - The data is invalid
    finally:
        shutil.rmtree(test_folder, ignore_errors=True)

@pytest.mark.skipif(
    is_running_on_travis_ci, reason="Requires manual testing")
def test_macos_no_keychain_entry_exists_before_first_use():
    test_folder = tempfile.mkdtemp(prefix="msal_extension_test_windows_token_cache_roundtrip")
    cache_file = os.path.join(test_folder, 'msal.cache')
    open(cache_file, 'w+')
    try:
        # Make sure key chain entry does not already exist for below service name
        persistence = KeychainPersistence(cache_file, "my_service_name", "my_account_name")
        assert persistence.load() is None  # ITEM_NOT_FOUND is handled
    finally:
        shutil.rmtree(test_folder, ignore_errors=True)
