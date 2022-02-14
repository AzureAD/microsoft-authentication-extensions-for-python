import logging
import json

from msal_extensions import build_encrypted_persistence, FilePersistence, CrossPlatLock


def build_persistence(location, fallback_to_plaintext=False):
    """Build a suitable persistence instance based your current OS"""
    # Note: This sample stores both encrypted persistence and plaintext persistence
    # into same location, therefore their data would likely override with each other.
    try:
        return build_encrypted_persistence(location)
    except:  # pylint: disable=bare-except
        # Known issue: Currently, only Linux
        if not fallback_to_plaintext:
            raise
        logging.warning("Encryption unavailable. Opting in to plain text.")
        return FilePersistence(location)

persistence = build_persistence("storage.bin", fallback_to_plaintext=False)
print("Type of persistence: {}".format(persistence.__class__.__name__))
print("Is this persistence encrypted?", persistence.is_encrypted)

data = {  # It can be anything, here we demonstrate an arbitrary json object
    "foo": "hello world",
    "bar": "",
    "service_principle_1": "blah blah...",
    }

with CrossPlatLock("my_another_lock.txt"):
    persistence.save(json.dumps(data))
    assert json.loads(persistence.load()) == data

