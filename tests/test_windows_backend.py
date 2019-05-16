import sys
import os
import pytest
import uuid
import msal

if not sys.platform.startswith('win'):
    pytest.skip('skipping windows-only tests', allow_module_level=True)
else:
    from msal_extensions._windows import WindowsDataProtectionAgent


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


def test_read_msal_cache():
    cache_locations = [
        os.path.join(os.getenv('LOCALAPPDATA'), '.IdentityService', 'msal.cache'), # this is where it's supposed to be
        os.path.join(os.getenv('LOCALAPPDATA'), '.IdentityServices', 'msal.cache'), # There was a miscommunications about whether this was plural or not.
        os.path.join(os.getenv('LOCALAPPDATA'), 'msal.cache'), # The earliest most naive builds used this locations.
    ]

    found = False
    for loc in cache_locations:
        try:
            with open(loc, mode='rb') as fh:
                contents = fh.read()
            found = True
            break
        except FileNotFoundError:
                pass
    if not found:
            pytest.skip('could not find the msal.cache file (try logging in using MSAL)')

    subject = WindowsDataProtectionAgent()
    raw = subject.unprotect(contents)
    assert raw != ""

    cache = msal.SerializableTokenCache()
    cache.deserialize(raw)
    access_tokens = cache.find(msal.TokenCache.CredentialType.ACCESS_TOKEN)
    assert len(access_tokens) > 0

