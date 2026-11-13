import json
import os
import shutil
import tempfile
from unittest.mock import patch
import sys
import runpy
import stat

import msal
import pytest

from msal_extensions import *
from .http_client import MinimalResponse


@pytest.fixture
def temp_location():
    test_folder = tempfile.mkdtemp(prefix="test_token_cache_roundtrip")
    yield os.path.join(test_folder, 'token_cache.bin')
    shutil.rmtree(test_folder, ignore_errors=True)

def _test_token_cache_roundtrip(persistence):
    desired_scopes = ['https://graph.microsoft.com/.default']
    apps = [  # Multiple apps sharing same persistence
        msal.ConfidentialClientApplication(
        "fake_client_id", client_credential="fake_client_secret",
        token_cache=PersistedTokenCache(persistence)) for i in range(2)]
    with patch.object(apps[0].http_client, "post", return_value=MinimalResponse(
        status_code=200, text=json.dumps({
            "token_type": "Bearer",
            "access_token": "app token",
            "expires_in": 3600,
    }))) as mocked_post:
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

@pytest.mark.skipif(os.name != "posix", reason="Requires POSIX file permissions")
def test_sample_plaintext_fallback_with_existing_marker(temp_location):
    marker = FilePersistence(temp_location)
    marker.touch()
    os.chmod(temp_location, 0o644)  # A marker left by an older native-store persistence.
    sample = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "sample", "token_cache_sample.py")
    with patch("msal_extensions.build_encrypted_persistence", return_value=marker) as builder:
        build_persistence = runpy.run_path(sample)["build_persistence"]
        builder.side_effect = RuntimeError("Native store unavailable")
        with pytest.raises(RuntimeError, match="Native store unavailable"):
            build_persistence(temp_location)
        persistence = build_persistence(temp_location, fallback_to_plaintext=True)

    cache = PersistedTokenCache(persistence)
    cache.add({
        "client_id": "test-client",
        "scope": ["test-scope"],
        "token_endpoint": "https://login.microsoftonline.com/test-tenant/oauth2/v2.0/token",
        "response": {"refresh_token": "synthetic-refresh-token"},
    })

    assert not cache.is_encrypted
    tokens = json.loads(persistence.load())["RefreshToken"].values()
    assert any(token["secret"] == "synthetic-refresh-token" for token in tokens)
    assert stat.S_IMODE(os.stat(temp_location).st_mode) == 0o600
