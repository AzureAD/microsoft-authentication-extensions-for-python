import sys
import os
import shutil
import tempfile
import pytest
import uuid
import msal

if not sys.platform.startswith('darwin'):
    pytest.skip('skipping MacOS-only tests', allow_module_level=True)
else:
    from msal_extensions.osx import Keychain
    from msal_extensions.token_cache import OSXTokenCache


def test_keychain_roundtrip():
    with Keychain() as subject:
        location, account = "msal_extension_test1", "test_account1"
        want = uuid.uuid4().hex
        subject.set_generic_password(location, account, want)
        got = subject.get_generic_password(location, account)
        assert got == want


def test_osx_token_cache_roundtrip():
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    if not (client_id and client_secret):
        pytest.skip('no credentials present to test OSXTokenCache round-trip with.')

    test_folder = tempfile.mkdtemp(prefix="msal_extension_test_osx_token_cache_roundtrip")
    cache_file = os.path.join(test_folder, 'msal.cache')
    try:
        subject = OSXTokenCache(cache_location=cache_file)
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            token_cache=subject)
        desired_scopes = ['https://graph.microsoft.com/.default']
        token1 = app.acquire_token_for_client(scopes=desired_scopes)
        os.utime(cache_file, None)  # Mock having another process update the cache.
        token2 = app.acquire_token_silent(scopes=desired_scopes, account=None)
        assert token1['access_token'] == token2['access_token']
    finally:
        shutil.rmtree(test_folder, ignore_errors=True)
