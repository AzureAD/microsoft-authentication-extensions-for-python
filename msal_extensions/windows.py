import os
import ctypes
from ctypes import wintypes
import time
import msal
import errno
from .cache_lock import CrossPlatLock

_local_free = ctypes.windll.kernel32.LocalFree
_memcpy = ctypes.cdll.msvcrt.memcpy
_crypt_protect_data = ctypes.windll.crypt32.CryptProtectData
_crypt_unprotect_data = ctypes.windll.crypt32.CryptUnprotectData
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DATA_BLOB(ctypes.Structure):
    """
    A wrapper for interacting with the _CRYPTOAPI_BLOB type and its many aliases. This type is exposed from Wincrypt.h
    in XP and above.

    See documentation for this type at:
    https://msdn.microsoft.com/en-us/7a06eae5-96d8-4ece-98cb-cf0710d2ddbd
    """
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def raw(self):
        # type: () -> bytes
        cb_data = int(self.cbData)
        pb_data = self.pbData
        buffer = ctypes.c_buffer(cb_data)
        _memcpy(buffer, pb_data, cb_data)
        _local_free(pb_data)
        return buffer.raw


# This code is modeled from a StackOverflow question, which can be found here:
# https://stackoverflow.com/questions/463832/using-dpapi-with-python
class WindowsDataProtectionAgent(object):

    def __init__(self, entropy=None):
        # type: (str) -> None
        self._entropy_blob = None
        if entropy:
            entropy_utf8 = entropy.encode('utf-8')
            buffer = ctypes.c_buffer(entropy_utf8, len(entropy_utf8))
            self._entropy_blob = DATA_BLOB(len(entropy_utf8), buffer)

    def protect(self, message):
        # type: (str) -> bytes

        message = message.encode('utf-8')
        message_buffer = ctypes.c_buffer(message, len(message))
        message_blob = DATA_BLOB(len(message), message_buffer)
        result = DATA_BLOB()

        if self._entropy_blob:
            entropy = ctypes.byref(self._entropy_blob)
        else:
            entropy = None

        if _crypt_protect_data(
                ctypes.byref(message_blob),
                u"python_data",
                entropy,
                None,
                None,
                _CRYPTPROTECT_UI_FORBIDDEN,
                ctypes.byref(result)):
            return result.raw()
        return b''

    def unprotect(self, cipher_text):
        # type: (bytes) -> str
        ct_buffer = ctypes.c_buffer(cipher_text, len(cipher_text))
        ct_blob = DATA_BLOB(len(cipher_text), ct_buffer)
        result = DATA_BLOB()

        if self._entropy_blob:
            entropy = ctypes.byref(self._entropy_blob)
        else:
            entropy = None

        if _crypt_unprotect_data(
            ctypes.byref(ct_blob),
            None,
            entropy,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(result)
        ):
            return result.raw().decode('utf-8')
        return u''


class WindowsTokenCache(msal.SerializableTokenCache):
    DEFAULT_CACHE_LOCATION = os.path.join(os.getenv('LOCALAPPDATA'), '.IdentityService', 'msal.cache')
    DEFAULT_ENTROPY = ''

    def __init__(self, **kwargs):
        super(WindowsTokenCache, self).__init__()

        self._cache_location = WindowsTokenCache.DEFAULT_CACHE_LOCATION  # type: str
        if 'cache_location' in kwargs:
            self._cache_location = kwargs['cache_location'] or WindowsTokenCache.DEFAULT_CACHE_LOCATION
        self._lock_location = self._cache_location + '.lockfile'

        entropy = WindowsTokenCache.DEFAULT_ENTROPY
        if 'entropy' in kwargs:
            entropy = kwargs['entropy']
        self._dp_agent = WindowsDataProtectionAgent(entropy=entropy)
        self._last_sync = 0  # _last_sync is a Unixtime

    def needs_refresh(self):
        # type: () -> Bool
        """
        Inspects the file holding the encrypted TokenCache to see if a read is necessary.
        :return: True if there are changes not reflected in memory, False otherwise.
        """
        try:
            return self._last_sync < os.path.getmtime(self._cache_location)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
            return False

    def add(self, event, **kwargs):
        with CrossPlatLock(self._lock_location):
            if self.needs_refresh():
                try:
                    self._read()
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise e
            super(WindowsTokenCache, self).add(event, **kwargs)
            self._write()

    def update_rt(self, rt_item, new_rt):
        with CrossPlatLock(self._lock_location):
            if self.needs_refresh():
                try:
                    self._read()
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise e
            super(WindowsTokenCache, self).update_rt(rt_item, new_rt)
            self._write()

    def remove_rt(self, rt_item):
        with CrossPlatLock(self._lock_location):
            if self.needs_refresh():
                try:
                    self._read()
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise e
            super(WindowsTokenCache, self).remove_rt(rt_item)
            self._write()

    def find(self, credential_type, target=None, query=None):
        with CrossPlatLock(self._lock_location):
            if self.needs_refresh():
                try:
                    self._read()
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise e
            return super(WindowsTokenCache, self).find(credential_type, target=target, query=query)

    def _write(self):
        with open(self._cache_location, 'wb') as fh:
            fh.write(self._dp_agent.protect(self.serialize()))
        self._last_sync = int(time.time())

    def _read(self):
        with open(self._cache_location, 'rb') as fh:
            cipher_text = fh.read()
        contents = self._dp_agent.unprotect(cipher_text)
        self.deserialize(contents)
        self._last_sync = int(time.time())
