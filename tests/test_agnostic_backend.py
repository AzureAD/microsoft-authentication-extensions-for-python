import os
import shutil
import tempfile
import sys

import msal
import pytest

from msal_extensions import *


@pytest.fixture
def temp_location():
    test_folder = tempfile.mkdtemp(prefix="test_token_cache_roundtrip")
    yield os.path.join(test_folder, 'token_cache.bin')
    shutil.rmtree(test_folder, ignore_errors=True)


def _test_token_cache_roundtrip(cache):
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    if not (client_id and client_secret):
        pytest.skip('no credentials present to test TokenCache round-trip with.')

    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        token_cache=cache)
    desired_scopes = ['https://graph.microsoft.com/.default']
    token1 = app.acquire_token_for_client(scopes=desired_scopes)
    os.utime(  # Mock having another process update the cache
        cache._persistence.get_location(), None)
    token2 = app.acquire_token_silent(scopes=desired_scopes, account=None)
    assert token1['access_token'] == token2['access_token']

def test_file_token_cache_roundtrip(temp_location):
    _test_token_cache_roundtrip(PersistedTokenCache(FilePersistence(temp_location)))

def test_current_platform_cache_roundtrip_with_persistence_builder(temp_location):
    _test_token_cache_roundtrip(PersistedTokenCache(build_encrypted_persistence(temp_location)))

def test_persisted_token_cache(temp_location):
    _test_token_cache_roundtrip(PersistedTokenCache(FilePersistence(temp_location)))

def test_file_not_found_error_is_not_raised():
    persistence = FilePersistence('non_existing_file')
    cache = PersistedTokenCache(persistence)
    # An exception raised here will fail the test case as it is supposed to be a NO-OP
    cache.find('')
