import sys
import logging
import json

from msal_extensions import build_encrypted_persistence, FilePersistence


def build_persistence(location, fallback_to_plaintext=False):
    """Build a suitable persistence instance based your current OS"""
    # Note: This sample stores both encrypted persistence and plaintext persistence
    # into same location, therefore their data would likely override with each other.
    try:
        return build_encrypted_persistence(location)
    except:  # pylint: disable=bare-except
        # On Linux, encryption exception will be raised during initialization.
        # On Windows and macOS, they won't be detected here,
        # but will be raised during their load() or save().
        if not fallback_to_plaintext:
            raise
        logging.warning("Encryption unavailable. Opting in to plain text.")
        return FilePersistence(location)

persistence = build_persistence("token_cache.bin")
print("Type of persistence: {}".format(persistence.__class__.__name__))
print("Is this persistence encrypted?", persistence.is_encrypted)

cache = PersistedTokenCache(persistence)
# Now you can use it in an msal application like this:
#   app = msal.PublicClientApplication("my_client_id", token_cache=cache)

