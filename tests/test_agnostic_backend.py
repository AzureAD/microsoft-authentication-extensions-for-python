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

def _test_token_cache_roundtrip(persistence):
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    if not (client_id and client_secret):
        pytest.skip('no credentials present to test TokenCache round-trip with.')

    desired_scopes = ['https://graph.microsoft.com/.default']
    apps = [  # Multiple apps sharing same persistence
        msal.ConfidentialClientApplication(
        client_id, client_credential=client_secret,
        token_cache=PersistedTokenCache(persistence)) for i in range(2)]
    token1 = apps[0].acquire_token_for_client(scopes=desired_scopes)
    assert token1["token_source"] == "identity_provider", "Initial token should come from IdP"
    token2 = apps[1].acquire_token_for_client(scopes=desired_scopes)  # Hit token cache in MSAL 1.23+
    assert token2["token_source"] == "cache", "App2 should hit cache written by app1"
    assert token1['access_token'] == token2['access_token'], "Cache should hit"

def test_token_cache_roundtrip_with_persistence_builder(temp_location):
    _test_token_cache_roundtrip(build_encrypted_persistence(temp_location))

def test_token_cache_roundtrip_with_file_persistence(temp_location):
    _test_token_cache_roundtrip(FilePersistence(temp_location))

def test_file_not_found_error_is_not_raised():
    persistence = FilePersistence('non_existing_file')
    cache = PersistedTokenCache(persistence)
    # An exception raised here will fail the test case as it is supposed to be a NO-OP
    cache.find('')
