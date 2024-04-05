import sys
import os
import errno
import shutil
import tempfile
import pytest
import uuid
import msal

if not sys.platform.startswith('win'):
    pytest.skip('skipping windows-only tests', allow_module_level=True)
else:
    from msal_extensions.windows import WindowsDataProtectionAgent
    from msal_extensions.token_cache import PersistedTokenCache
    from msal_extensions.persistence import FilePersistenceWithDataProtection


def test_dpapi_roundtrip_with_entropy():
    subject_without_entropy = WindowsDataProtectionAgent()
    subject_with_entropy = WindowsDataProtectionAgent(entropy=uuid.uuid4().hex)

    test_cases = [
        '',
        'lorem ipsum',
        'lorem-ipsum',
        '<Python>',
        uuid.uuid4().hex,
    ]

    for tc in test_cases:
        ciphered = subject_with_entropy.protect(tc)
        assert ciphered != tc

        got = subject_with_entropy.unprotect(ciphered)
        assert got == tc

        ciphered = subject_without_entropy.protect(tc)
        assert ciphered != tc

        got = subject_without_entropy.unprotect(ciphered)
        assert got == tc


def test_read_msal_cache_direct():
    """
    This loads and unprotects an MSAL cache directly, only using the DataProtectionAgent.
    """
    localappdata_location = os.getenv('LOCALAPPDATA', os.path.expanduser('~'))
    cache_locations = [
        os.path.join(localappdata_location, '.IdentityService', 'msal.cache'), # this is where it's supposed to be
        os.path.join(localappdata_location, '.IdentityServices', 'msal.cache'), # There was a miscommunications about whether this was plural or not.
        os.path.join(localappdata_location, 'msal.cache'), # The earliest most naive builds used this locations.
    ]

    found = False
    for loc in cache_locations:
        try:
            with open(loc, mode='rb') as fh:
                contents = fh.read()
            found = True

            break
        except IOError as exp:
            if exp.errno != errno.ENOENT:
                raise exp

    if not found:
            pytest.skip('could not find the msal.cache file (try logging in using MSAL)')

    subject = WindowsDataProtectionAgent()
    raw = subject.unprotect(contents)
    assert raw != ""

    cache = msal.SerializableTokenCache()
    cache.deserialize(raw)
    access_tokens = cache.find(msal.TokenCache.CredentialType.ACCESS_TOKEN)
    assert len(access_tokens) > 0


def test_windows_token_cache_roundtrip():
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    if not (client_id and client_secret):
        pytest.skip('no credentials present to test PersistedTokenCache round-trip with.')

    test_folder = tempfile.mkdtemp(prefix="msal_extension_test_windows_token_cache_roundtrip")
    cache_file = os.path.join(test_folder, 'msal.cache')
    try:
        subject = PersistedTokenCache(FilePersistenceWithDataProtection(cache_file))
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            token_cache=subject)
        desired_scopes = ['https://graph.microsoft.com/.default']
        token1 = app.acquire_token_for_client(scopes=desired_scopes)
        # TODO: Modify this to same approach in test_agnostic_backend.py
        os.utime(cache_file, None)  # Mock having another process update the cache.
        token2 = app.acquire_token_silent(scopes=desired_scopes, account=None)
        assert token1['access_token'] == token2['access_token']
    finally:
        shutil.rmtree(test_folder, ignore_errors=True)
