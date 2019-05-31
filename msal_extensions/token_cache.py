"""Generic functions and types for working with a TokenCache that is not platform specific."""
import os
import sys
import time
import errno
import msal
from .cache_lock import CrossPlatLock

if sys.platform.startswith('win'):
    from .windows import WindowsDataProtectionAgent
elif sys.platform.startswith('darwin'):
    from .osx import Keychain


def get_protected_token_cache(enforce_encryption=False, **kwargs):
    """Detects the current system, and constructs a TokenCache of the appropriate type for the
    environment in which it's running.

    :param enforce_encryption: When 'True' an error will be raised if there isn't an encrypted
    option available for the current system. When 'False', a plain-text option will be returned.
    :param kwargs: Any options that should be passed to the platform-specific constructor of the
    TokenCache being instantiated by this method.
    :return: A fully instantiated TokenCache able to encrypt/decrypt tokens on the current system.
    """
    if sys.platform.startswith('win'):
        return WindowsTokenCache(**kwargs)

    if sys.platform.startswith('darwin'):
        return OSXTokenCache(**kwargs)

    if enforce_encryption:
        raise RuntimeError('no protected token cache for platform {}'.format(sys.platform))

    raise NotImplementedError('No fallback TokenCache is implemented yet.')

def _mkdir_p(path):
    """Creates a directory, and any necessary parents.

    This implementation based on a Stack Overflow question that can be found here:
    https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python

    If the path provided is an existing file, this function raises an exception.
    :param path: The directory name that should be created.
    """
    try:
        os.mkdir(path)
    except OSError as exp:
        if exp.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class FileTokenCache(msal.SerializableTokenCache):
    """Implements basic unprotected SerializableTokenCache to a plain-text file."""
    def __init__(self,
                 cache_location=os.path.join(
                     os.getenv('LOCALAPPDATA', os.path.expanduser('~')),
                     '.IdentityService',
                     'msal.cache'),
                 lock_location=None):
        super(FileTokenCache, self).__init__()
        self._cache_location = cache_location
        self._lock_location = lock_location or self._cache_location + '.lockfile'
        self._last_sync = 0  # _last_sync is a Unixtime

        self._cache_location = os.path.expanduser(self._cache_location)
        self._lock_location = os.path.expanduser(self._lock_location)

        _mkdir_p(os.path.dirname(self._lock_location))
        _mkdir_p(os.path.dirname(self._cache_location))

    def _needs_refresh(self):
        # type: () -> Bool
        """
        Inspects the file holding the encrypted TokenCache to see if a read is necessary.
        :return: True if there are changes not reflected in memory, False otherwise.
        """
        try:
            return self._last_sync < os.path.getmtime(self._cache_location)
        except IOError as exp:
            if exp.errno != errno.ENOENT:
                raise exp
            return False

    def _write(self):
        """Handles actually committing the serialized form of this TokenCache to persisted storage.
        For types derived of this, class that will be a file, whcih has the ability to track a last
        modified time.
        """
        with open(self._cache_location, 'wb') as handle:
            handle.write(self.serialize())

    def _read(self):
        """Fetches the contents of a file and invokes deserialization."""
        with open(self._cache_location, 'rb') as handle:
            contents = handle.read()
        self.deserialize(contents)

    def add(self, event, **kwargs):
        with CrossPlatLock(self._lock_location):
            if self._needs_refresh():
                try:
                    self._read()
                except IOError as exp:
                    if exp.errno != errno.ENOENT:
                        raise exp
            super(FileTokenCache, self).add(event, **kwargs)  # pylint: disable=duplicate-code
            self._write()

    def modify(self, credential_type, old_entry, new_key_value_pairs=None):
        with CrossPlatLock(self._lock_location):
            if self._needs_refresh():
                try:
                    self._read()
                except IOError as exp:
                    if exp.errno != errno.ENOENT:
                        raise exp
            super(FileTokenCache, self).modify(
                credential_type,
                old_entry,
                new_key_value_pairs=new_key_value_pairs)
            self._write()

    def find(self, credential_type, **kwargs):  # pylint: disable=arguments-differ
        with CrossPlatLock(self._lock_location):
            if self._needs_refresh():
                try:
                    self._read()
                except IOError as exp:
                    if exp.errno != errno.ENOENT:
                        raise exp
            return super(FileTokenCache, self).find(credential_type, **kwargs)

    def __getattr__(self, item):
        # Instead of relying on implementers remembering to update _last_sync, just detect that one
        # of the relevant methods has been called take care of it for derived types.
        if item in ['_read', '_write']:
            self._last_sync = int(time.time())
        return super(FileTokenCache, self).__getattr__(item)  # pylint: disable=no-member


class WindowsTokenCache(FileTokenCache):
    """A SerializableTokenCache implementation which uses Win32 encryption APIs to protect your
    tokens.
    """
    def __init__(self,
                 cache_location=None,
                 lock_location=None,
                 entropy=''):
        super(WindowsTokenCache, self).__init__(
            cache_location=cache_location,
            lock_location=lock_location)
        self._dp_agent = WindowsDataProtectionAgent(entropy=entropy)

    def _write(self):
        with open(self._cache_location, 'wb') as handle:
            handle.write(self._dp_agent.protect(self.serialize()))

    def _read(self):
        with open(self._cache_location, 'rb') as handle:
            cipher_text = handle.read()
        contents = self._dp_agent.unprotect(cipher_text)
        self.deserialize(contents)


class OSXTokenCache(FileTokenCache):
    """A SerializableTokenCache implementation which uses native Keychain libraries to protect your
    tokens.
    """

    def __init__(self,
                 cache_location='~/.IdentityService/msal.cache',
                 lock_location=None,
                 service_name='Microsoft.Developer.IdentityService',
                 account_name='MSALCache'):
        super(OSXTokenCache, self).__init__(cache_location=cache_location,
                                            lock_location=lock_location)
        self._service_name = service_name
        self._account_name = account_name

    def _read(self):
        with Keychain() as locker:
            contents = locker.get_generic_password(self._service_name, self._account_name)
        self.deserialize(contents)

    def _write(self):
        with Keychain() as locker:
            locker.set_generic_password(self._service_name, self._account_name, self.serialize())
