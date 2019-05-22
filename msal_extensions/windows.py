import os
import ctypes
from ctypes import wintypes
import time
import errno
import msal
from .cache_lock import CrossPlatLock

_local_free = ctypes.windll.kernel32.LocalFree
_memcpy = ctypes.cdll.msvcrt.memcpy
_crypt_protect_data = ctypes.windll.crypt32.CryptProtectData
_crypt_unprotect_data = ctypes.windll.crypt32.CryptUnprotectData
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DataBlob(ctypes.Structure):
    """A wrapper for interacting with the _CRYPTOAPI_BLOB type and its many aliases. This type is
    exposed from Wincrypt.h in XP and above.

    See documentation for this type at:
    https://msdn.microsoft.com/en-us/7a06eae5-96d8-4ece-98cb-cf0710d2ddbd
    """
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def __del__(self):
        if self.pbData and self.cbData > 0:
            _local_free(self.pbData)

    def raw(self):
        # type: () -> bytes
        cb_data = int(self.cbData)
        pb_data = self.pbData
        buffer = ctypes.create_string_buffer(cb_data)
        _memcpy(buffer, pb_data, cb_data)
        return buffer.raw


# This code is modeled from a StackOverflow question, which can be found here:
# https://stackoverflow.com/questions/463832/using-dpapi-with-python
class WindowsDataProtectionAgent(object):

    def __init__(self, entropy=None):
        # type: (str) -> None
        self._entropy_blob = None
        if entropy:
            entropy_utf8 = entropy.encode('utf-8')
            buffer = ctypes.create_string_buffer(entropy_utf8, len(entropy_utf8))
            self._entropy_blob = DataBlob(len(entropy_utf8), buffer)

    def protect(self, message):
        # type: (str) -> bytes

        message = message.encode('utf-8')
        message_buffer = ctypes.create_string_buffer(message, len(message))
        message_blob = DataBlob(len(message), message_buffer)
        result = DataBlob()

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
        ct_buffer = ctypes.create_string_buffer(cipher_text, len(cipher_text))
        ct_blob = DataBlob(len(cipher_text), ct_buffer)
        result = DataBlob()

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
    """A SerializableTokenCache implementation which uses Win32 encryption APIs to protect your
    tokens.
    """
    def __init__(self,
                 cache_location=os.path.join(
                     os.getenv('LOCALAPPDATA'),
                     '.IdentityService',
                     'msal.cache'),
                 entropy=''):
        super(WindowsTokenCache, self).__init__()

        self._cache_location = cache_location
        self._lock_location = self._cache_location + '.lockfile'
        self._dp_agent = WindowsDataProtectionAgent(entropy=entropy)
        self._last_sync = 0  # _last_sync is a Unixtime

    def _needs_refresh(self):
        # type: () -> Bool
        """
        Inspects the file holding the encrypted TokenCache to see if a read is necessary.
        :return: True if there are changes not reflected in memory, False otherwise.
        """
        try:
            return self._last_sync < os.path.getmtime(self._cache_location)
        except OSError as exp:
            if exp.errno != errno.ENOENT:
                raise exp
            return False

    def add(self, event, **kwargs):
        with CrossPlatLock(self._lock_location):
            if self._needs_refresh():
                try:
                    self._read()
                except OSError as exp:
                    if exp.errno != errno.ENOENT:
                        raise exp
            super(WindowsTokenCache, self).add(event, **kwargs)
            self._write()

    def update_rt(self, rt_item, new_rt):
        with CrossPlatLock(self._lock_location):
            if self._needs_refresh():
                try:
                    self._read()
                except OSError as exp:
                    if exp.errno != errno.ENOENT:
                        raise exp
            super(WindowsTokenCache, self).update_rt(rt_item, new_rt)
            self._write()

    def remove_rt(self, rt_item):
        with CrossPlatLock(self._lock_location):
            if self._needs_refresh():
                try:
                    self._read()
                except OSError as exp:
                    if exp.errno != errno.ENOENT:
                        raise exp
            super(WindowsTokenCache, self).remove_rt(rt_item)
            self._write()

    def find(self, credential_type, **kwargs):
        with CrossPlatLock(self._lock_location):
            if self._needs_refresh():
                try:
                    self._read()
                except OSError as exp:
                    if exp.errno != errno.ENOENT:
                        raise exp
            return super(WindowsTokenCache, self).find(credential_type, **kwargs)

    def _write(self):
        with open(self._cache_location, 'wb') as handle:
            handle.write(self._dp_agent.protect(self.serialize()))
        self._last_sync = int(time.time())

    def _read(self):
        with open(self._cache_location, 'rb') as handle:
            cipher_text = handle.read()
        contents = self._dp_agent.unprotect(cipher_text)
        self.deserialize(contents)
        self._last_sync = int(time.time())
