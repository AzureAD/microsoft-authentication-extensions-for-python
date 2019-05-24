"""Implements a macOS specific TokenCache, and provides auxiliary helper types."""
import os
import ctypes as _ctypes
import time
import msal

OS_RESULT = _ctypes.c_int32


class KeychainError(OSError):
    """The parent of all exceptions that may be thrown by the functions implemented inside of the
    Keychain type."""
    def __init__(self, exit_status):
        super(KeychainError, self).__init__()
        self.exit_status = exit_status
        # TODO: pylint: disable=fixme
        #  use SecCopyErrorMessageString to fetch the appropriate message here.
        self.message = \
            '{} ' \
            'see https://opensource.apple.com/source/CarbonHeaders/CarbonHeaders-18.1/MacErrors.h'\
                .format(self.exit_status)


class KeychainAccessDeniedError(KeychainError):
    """The exceptions that's raised when a Keychain is set to be queried, but the current process
    has not been give permission to access it, and a query comes anyway."""
    EXIT_STATUS = -128

    def __init__(self):
        super(KeychainAccessDeniedError, self).__init__(KeychainAccessDeniedError.EXIT_STATUS)


class NoSuchKeychainError(KeychainError):
    """The exception that's raised when a Keychain is set to be queried, but it is non-existent, and
    a query comes anyway."""
    EXIT_STATUS = -25294

    def __init__(self, name):
        super(NoSuchKeychainError, self).__init__(NoSuchKeychainError.EXIT_STATUS)
        self.name = name


class NoDefaultKeychainError(KeychainError):
    """The exception that's raised when no Keychain is set to be queried, but a query comes
    anyway.
    """
    EXIT_STATUS = -25307

    def __init__(self):
        super(NoDefaultKeychainError, self).__init__(NoDefaultKeychainError.EXIT_STATUS)


class KeychainItemNotFoundError(KeychainError):
    """The exception that's raised when a non-exist Keychain entry is requested."""
    EXIT_STATUS = -25300

    def __init__(self, service_name, account_name):
        super(KeychainItemNotFoundError, self).__init__(KeychainItemNotFoundError.EXIT_STATUS)
        self.service_name = service_name
        self.account_name = account_name


def _construct_error(exit_status, **kwargs):
    if exit_status == KeychainAccessDeniedError.EXIT_STATUS:
        return KeychainAccessDeniedError()
    if exit_status == NoSuchKeychainError.EXIT_STATUS:
        return NoSuchKeychainError(**kwargs)
    if exit_status == NoDefaultKeychainError.EXIT_STATUS:
        return NoDefaultKeychainError()
    if exit_status == KeychainItemNotFoundError.EXIT_STATUS:
        return KeychainItemNotFoundError(**kwargs)
    return KeychainError(exit_status)


def _get_native_location(name):
    # type: (str) -> str
    """
    Fetches the location of a native MacOS library.
    :param name: The name of the library to be loaded.
    :return: The location of the library on a MacOS filesystem.
    """
    return '/System/Library/Frameworks/{0}.framework/{0}'.format(name)


# Load native MacOS libraries
try:
    _SECURITY = _ctypes.CDLL(_get_native_location('Security'))
    _CORE = _ctypes.CDLL(_get_native_location('CoreFoundation'))
except OSError:
    _SECURITY = None
    _CORE = None

# Bind CFRelease from native MacOS libraries.
_CORE_RELEASE = _CORE.CFRelease
_CORE_RELEASE.argtypes = (
    _ctypes.c_void_p,
)

# Bind SecCopyErrorMessageString from native MacOS libraries.
# https://developer.apple.com/documentation/security/1394686-seccopyerrormessagestring?language=objc
_SECURITY_COPY_ERROR_MESSAGE_STRING = _SECURITY.SecCopyErrorMessageString
_SECURITY_COPY_ERROR_MESSAGE_STRING.argtypes = (
    OS_RESULT,
    _ctypes.c_void_p
)
_SECURITY_COPY_ERROR_MESSAGE_STRING.restype = _ctypes.c_char_p

# Bind SecKeychainOpen from native MacOS libraries.
# https://developer.apple.com/documentation/security/1396431-seckeychainopen
_SECURITY_KEYCHAIN_OPEN = _SECURITY.SecKeychainOpen
_SECURITY_KEYCHAIN_OPEN.argtypes = (
    _ctypes.c_char_p,
    _ctypes.POINTER(_ctypes.c_void_p)
)
_SECURITY_KEYCHAIN_OPEN.restype = OS_RESULT

# Bind SecKeychainCopyDefault from native MacOS libraries.
# https://developer.apple.com/documentation/security/1400743-seckeychaincopydefault?language=objc
_SECURITY_KEYCHAIN_COPY_DEFAULT = _SECURITY.SecKeychainCopyDefault
_SECURITY_KEYCHAIN_COPY_DEFAULT.argtypes = (
    _ctypes.POINTER(_ctypes.c_void_p),
)
_SECURITY_KEYCHAIN_COPY_DEFAULT.restype = OS_RESULT


# Bind SecKeychainItemFreeContent from native MacOS libraries.
_SECURITY_KEYCHAIN_ITEM_FREE_CONTENT = _SECURITY.SecKeychainItemFreeContent
_SECURITY_KEYCHAIN_ITEM_FREE_CONTENT.argtypes = (
    _ctypes.c_void_p,
    _ctypes.c_void_p,
)
_SECURITY_KEYCHAIN_ITEM_FREE_CONTENT.restype = OS_RESULT

# Bind SecKeychainItemModifyAttributesAndData from native MacOS libraries.
_SECURITY_KEYCHAIN_ITEM_MODIFY_ATTRIBUTES_AND_DATA = \
    _SECURITY.SecKeychainItemModifyAttributesAndData
_SECURITY_KEYCHAIN_ITEM_MODIFY_ATTRIBUTES_AND_DATA.argtypes = (
    _ctypes.c_void_p,
    _ctypes.c_void_p,
    _ctypes.c_uint32,
    _ctypes.c_void_p,
)
_SECURITY_KEYCHAIN_ITEM_MODIFY_ATTRIBUTES_AND_DATA.restype = OS_RESULT

# Bind SecKeychainFindGenericPassword from native MacOS libraries.
# https://developer.apple.com/documentation/security/1397301-seckeychainfindgenericpassword?language=objc
_SECURITY_KEYCHAIN_FIND_GENERIC_PASSWORD = _SECURITY.SecKeychainFindGenericPassword
_SECURITY_KEYCHAIN_FIND_GENERIC_PASSWORD.argtypes = (
    _ctypes.c_void_p,
    _ctypes.c_uint32,
    _ctypes.c_char_p,
    _ctypes.c_uint32,
    _ctypes.c_char_p,
    _ctypes.POINTER(_ctypes.c_uint32),
    _ctypes.POINTER(_ctypes.c_void_p),
    _ctypes.POINTER(_ctypes.c_void_p),
)
_SECURITY_KEYCHAIN_FIND_GENERIC_PASSWORD.restype = OS_RESULT
# Bind SecKeychainAddGenericPassword from native MacOS
# https://developer.apple.com/documentation/security/1398366-seckeychainaddgenericpassword?language=objc
_SECURITY_KEYCHAIN_ADD_GENERIC_PASSWORD = _SECURITY.SecKeychainAddGenericPassword
_SECURITY_KEYCHAIN_ADD_GENERIC_PASSWORD.argtypes = (
    _ctypes.c_void_p,
    _ctypes.c_uint32,
    _ctypes.c_char_p,
    _ctypes.c_uint32,
    _ctypes.c_char_p,
    _ctypes.c_uint32,
    _ctypes.c_char_p,
    _ctypes.POINTER(_ctypes.c_void_p),
)
_SECURITY_KEYCHAIN_ADD_GENERIC_PASSWORD.restype = OS_RESULT


class Keychain(object):
    """Encapsulates the interactions with a particular MacOS Keychain."""
    def __init__(self, filename=None):
        # type: (str) -> None
        self._ref = _ctypes.c_void_p()

        if filename:
            filename = os.path.expanduser(filename)
            self._filename = filename.encode('utf-8')
        else:
            self._filename = None

    def __enter__(self):
        if self._filename:
            status = _SECURITY_KEYCHAIN_OPEN(self._filename, self._ref)
        else:
            status = _SECURITY_KEYCHAIN_COPY_DEFAULT(self._ref)

        if status:
            raise OSError(status)
        return self

    def __exit__(self, *args):
        if self._ref:
            _CORE_RELEASE(self._ref)

    def get_generic_password(self, service, account_name):
        # type: (str, str) -> str
        """Fetch the password associated with a particular service and account.

        :param service: The service that this password is associated with.
        :param account_name: The account that this password is associated with.
        :return: The value of the password associated with the specified service and account.
        """
        service = service.encode('utf-8')
        account_name = account_name.encode('utf-8')

        length = _ctypes.c_uint32()
        contents = _ctypes.c_void_p()
        exit_status = _SECURITY_KEYCHAIN_FIND_GENERIC_PASSWORD(
            self._ref,
            len(service),
            service,
            len(account_name),
            account_name,
            length,
            contents,
            None,
        )

        if exit_status:
            raise _construct_error(
                exit_status=exit_status,
                service_name=service,
                account_name=account_name)

        value = _ctypes.create_string_buffer(length.value)
        _ctypes.memmove(value, contents.value, length.value)
        _SECURITY_KEYCHAIN_ITEM_FREE_CONTENT(None, contents)
        return value.raw.decode('utf-8')

    def set_generic_password(self, service, account_name, value):
        # type: (str, str, str) -> None
        """Associate a password with a given service and account.

        :param service: The service to associate this password with.
        :param account_name: The account to associate this password with.
        :param value: The string that should be used as the password.
        """
        service = service.encode('utf-8')
        account_name = account_name.encode('utf-8')
        value = value.encode('utf-8')

        entry = _ctypes.c_void_p()
        find_exit_status = _SECURITY_KEYCHAIN_FIND_GENERIC_PASSWORD(
            self._ref,
            len(service),
            service,
            len(account_name),
            account_name,
            None,
            None,
            entry,
        )

        if not find_exit_status:
            modify_exit_status = _SECURITY_KEYCHAIN_ITEM_MODIFY_ATTRIBUTES_AND_DATA(
                entry,
                None,
                len(value),
                value,
            )
            if modify_exit_status:
                raise _construct_error(
                    modify_exit_status,
                    service_name=service,
                    account_name=account_name)

        elif find_exit_status == KeychainItemNotFoundError.EXIT_STATUS:
            add_exit_status = _SECURITY_KEYCHAIN_ADD_GENERIC_PASSWORD(
                self._ref,
                len(service),
                service,
                len(account_name),
                account_name,
                len(value),
                value,
                None
            )

            if add_exit_status:
                raise _construct_error(
                    add_exit_status,
                    service_name=service,
                    account_name=account_name)
        else:
            raise _construct_error(
                find_exit_status,
                service_name=service,
                account_name=account_name)

    def get_internet_password(self, service, username):
        # type: (str, str) -> str
        """ Fetches a password associated with a domain and username.
        NOTE: THIS IS NOT YET IMPLEMENTED
        :param service: The website/service that this password is associated with.
        :param username: The account that this password is associated with.
        :return: The password that was associated with the given service and username.
        """
        raise NotImplementedError()

    def set_internet_password(self, service, username, value):
        # type: (str, str, str) -> None
        """Sets a password associated with a domain and a username.
        NOTE: THIS IS NOT YET IMPLEMENTED
        :param service: The website/service that this password is associated with.
        :param username: The account that this password is associated with.
        :param value: The password that should be associated with the given service and username.
        """
        raise NotImplementedError()


class OSXTokenCache(msal.SerializableTokenCache):
    """A SerializableTokenCache implementation which uses native Keychain libraries to protect your
    tokens.
    """

    def __init__(self,
                 service_name='Microsoft.Developer.IdentityService',
                 account_name='MSALCache'):
        super(OSXTokenCache, self).__init__()
        self._service_name = service_name
        self._account_name = account_name
        self._last_sync = 0

    def add(self, event, **kwargs):
        super(OSXTokenCache, self).add(event, **kwargs)
        self._write()

    def update_rt(self, rt_item, new_rt):
        super(OSXTokenCache, self).update_rt(rt_item, new_rt)
        self._write()

    def remove_rt(self, rt_item):
        super(OSXTokenCache, self).remove_rt(rt_item)
        self._write()

    def find(self, credential_type, **kwargs):  # pylint: disable=arguments-differ
        self._read()
        return super(OSXTokenCache, self).find(credential_type, **kwargs)

    def _read(self):
        with Keychain() as locker:
            contents = locker.get_generic_password(self._service_name, self._account_name)
        self.deserialize(contents)
        self._last_sync = int(time.time())

    def _write(self):
        with Keychain() as locker:
            locker.set_generic_password(self._service_name, self._account_name, self.serialize())
        self._last_sync = int(time.time())
