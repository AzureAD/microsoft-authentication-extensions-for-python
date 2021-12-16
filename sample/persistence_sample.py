import sys
import logging
import json

from msal_extensions import *


def build_persistence(location, fallback_to_plaintext=False):
    """Build a suitable persistence instance based your current OS"""
    if sys.platform.startswith('win'):
        return FilePersistenceWithDataProtection(location)
    if sys.platform.startswith('darwin'):
        return KeychainPersistence(location)
    if sys.platform.startswith('linux'):
        try:
            return LibsecretPersistence(
                # By using same location as the fall back option below,
                # this would override the unencrypted data stored by the
                # fall back option.  It is probably OK, or even desirable
                # (in order to aggressively wipe out plain-text persisted data),
                # unless there would frequently be a desktop session and
                # a remote ssh session being active simultaneously.
                location,
                )
        except:  # pylint: disable=bare-except
            if not fallback_to_plaintext:
                raise
            logging.warning("Encryption unavailable. Opting in to plain text.")
    return FilePersistence(location)

persistence = build_persistence(
    "storage.bin", fallback_to_plaintext=False,
    data_conversion=json,
    lock=CrossPlatLock("my_another_lock.txt"),
    )
print("Type of persistence: {}".format(persistence.__class__.__name__))
print("Is this persistence encrypted?", persistence.is_encrypted)

data = {  # It can be anything, here we demonstrate an arbitrary json object
    "foo": "hello world",
    "bar": "",
    "service_principle_1": "blah blah...",
    }

persistence.save(data)
assert persistence.load(default={}) == data
"""
with CrossPlatLock("my_another_lock.txt"):
    persistence.save(json.dumps(data))
    assert json.loads(persistence.load()) == data
"""
