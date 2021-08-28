"""Implements a Windows Specific TokenCache, and provides auxiliary helper types."""
import ctypes
from ctypes import wintypes

_LOCAL_FREE = ctypes.windll.kernel32.LocalFree
_GET_LAST_ERROR = ctypes.windll.kernel32.GetLastError
_MEMCPY = ctypes.cdll.msvcrt.memcpy
_MEMCPY.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]  # Note:
    # Suggested by https://github.com/AzureAD/microsoft-authentication-extensions-for-python/issues/85  # pylint: disable=line-too-long
    # Matching https://docs.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy?view=msvc-160  # pylint: disable=line-too-long
_CRYPT_PROTECT_DATA = ctypes.windll.crypt32.CryptProtectData
_CRYPT_UNPROTECT_DATA = ctypes.windll.crypt32.CryptUnprotectData
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DataBlob(ctypes.Structure):  # pylint: disable=too-few-public-methods
    """A wrapper for interacting with the _CRYPTOAPI_BLOB type and its many aliases. This type is
    exposed from Wincrypt.h in XP and above.

    The memory associated with a DataBlob itself does not need to be freed, as the Python runtime
    will correctly clean it up. However, depending on the data it points at, it may still need to be
    freed. For instance, memory created by ctypes.create_string_buffer is already managed, and needs
    to not be freed. However, memory allocated by CryptProtectData and CryptUnprotectData must have
    LocalFree called on pbData.

    See documentation for this type at:
    https://msdn.microsoft.com/en-us/7a06eae5-96d8-4ece-98cb-cf0710d2ddbd
    """
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def raw(self):
        # type: () -> bytes
        """Copies the message from the DataBlob in natively allocated memory into Python controlled
        memory.
        :return A byte array that matches what is stored in native-memory."""
        cb_data = int(self.cbData)
        pb_data = self.pbData
        blob_buffer = ctypes.create_string_buffer(cb_data)
        _MEMCPY(blob_buffer, pb_data, cb_data)
        return blob_buffer.raw


# This code is modeled from a StackOverflow question, which can be found here:
# https://stackoverflow.com/questions/463832/using-dpapi-with-python
class WindowsDataProtectionAgent(object):
    """A mechanism for interacting with the Windows DP API Native library, e.g. Crypt32.dll."""

    def __init__(self, entropy=None):
        # type: (str) -> None
        self._entropy_blob = None
        if entropy:
            entropy_utf8 = entropy.encode('utf-8')
            blob_buffer = ctypes.create_string_buffer(entropy_utf8, len(entropy_utf8))
            self._entropy_blob = DataBlob(len(entropy_utf8), blob_buffer)

    def protect(self, message):
        # type: (str) -> bytes
        """Encrypts a message.
        :return cipher text holding the original message."""

        message = message.encode('utf-8')
        message_buffer = ctypes.create_string_buffer(message, len(message))
        message_blob = DataBlob(len(message), message_buffer)
        result = DataBlob()

        if self._entropy_blob:
            entropy = ctypes.byref(self._entropy_blob)
        else:
            entropy = None

        if _CRYPT_PROTECT_DATA(
                ctypes.byref(message_blob),
                u"python_data",  # pylint: disable=redundant-u-string-prefix
                entropy,
                None,
                None,
                _CRYPTPROTECT_UI_FORBIDDEN,
                ctypes.byref(result)):
            try:
                return result.raw()
            finally:
                _LOCAL_FREE(result.pbData)

        err_code = _GET_LAST_ERROR()
        raise OSError(256, '', '', err_code)

    def unprotect(self, cipher_text):
        # type: (bytes) -> str
        """Decrypts cipher text that is provided.
        :return The original message hidden in the cipher text."""
        ct_buffer = ctypes.create_string_buffer(cipher_text, len(cipher_text))
        ct_blob = DataBlob(len(cipher_text), ct_buffer)
        result = DataBlob()

        if self._entropy_blob:
            entropy = ctypes.byref(self._entropy_blob)
        else:
            entropy = None

        if _CRYPT_UNPROTECT_DATA(
                ctypes.byref(ct_blob),
                None,
                entropy,
                None,
                None,
                _CRYPTPROTECT_UI_FORBIDDEN,
                ctypes.byref(result)
        ):
            try:
                return result.raw().decode('utf-8')
            finally:
                _LOCAL_FREE(result.pbData)
        err_code = _GET_LAST_ERROR()
        raise OSError(256, '', '', err_code)
