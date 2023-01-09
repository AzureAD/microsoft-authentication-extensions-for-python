# pylint: disable=duplicate-code

"""Implements a macOS specific TokenCache, and provides auxiliary helper types."""

import ctypes as _ctypes
import os

OS_RESULT = _ctypes.c_int32  # pylint: disable=invalid-name


class CFString(_ctypes.Structure):
    # https://developer.apple.com/documentation/_COREfoundation/cfstring
    pass


CFIndex = _ctypes.c_int
kCFStringEncodingUTF8 = 0x08000100
CFStringRef = _ctypes.POINTER(CFString)


class KeychainError(OSError):
    """The RuntimeError that will be run when a function interacting with Keychain fails."""

    ACCESS_DENIED = -128
    NO_SUCH_KEYCHAIN = -25294
    NO_DEFAULT = -25307
    ITEM_NOT_FOUND = -25300

    def __init__(self, exit_status):
        super(KeychainError, self).__init__()
        self.exit_status = exit_status
        self.message = getSecErrorStr(exit_status)


def _get_native_location(name):
    # type: (str) -> str
    """
    Fetches the location of a native MacOS library.
    :param name: The name of the library to be loaded.
    :return: The location of the library on a MacOS filesystem.
    """
    return "/System/Library/Frameworks/{0}.framework/{0}".format(
        name
    )  # pylint: disable=consider-using-f-string


# Load native MacOS libraries
_SECURITY = _ctypes.CDLL(_get_native_location("Security"))
_CORE = _ctypes.CDLL(_get_native_location("CoreFoundation"))

# Bind CFRelease from native MacOS libraries.
_CORE_RELEASE = _CORE.CFRelease
_CORE_RELEASE.argtypes = (_ctypes.c_void_p,)

# Bind SecCopyErrorMessageString from native MacOS libraries.
# https://developer.apple.com/documentation/security/1394686-seccopyerrormessagestring?language=objc
_SECURITY_COPY_ERROR_MESSAGE_STRING = _SECURITY.SecCopyErrorMessageString
_SECURITY_COPY_ERROR_MESSAGE_STRING.argtypes = (OS_RESULT, _ctypes.c_void_p)
_SECURITY_COPY_ERROR_MESSAGE_STRING.restype = _ctypes.c_char_p

# Bind SecKeychainOpen from native MacOS libraries.
# https://developer.apple.com/documentation/security/1396431-seckeychainopen
_SECURITY_KEYCHAIN_OPEN = _SECURITY.SecKeychainOpen
_SECURITY_KEYCHAIN_OPEN.argtypes = (_ctypes.c_char_p, _ctypes.POINTER(_ctypes.c_void_p))
_SECURITY_KEYCHAIN_OPEN.restype = OS_RESULT

# Bind SecKeychainCopyDefault from native MacOS libraries.
# https://developer.apple.com/documentation/security/1400743-seckeychaincopydefault?language=objc
_SECURITY_KEYCHAIN_COPY_DEFAULT = _SECURITY.SecKeychainCopyDefault
_SECURITY_KEYCHAIN_COPY_DEFAULT.argtypes = (_ctypes.POINTER(_ctypes.c_void_p),)
_SECURITY_KEYCHAIN_COPY_DEFAULT.restype = OS_RESULT


# Bind SecKeychainItemFreeContent from native MacOS libraries.
_SECURITY_KEYCHAIN_ITEM_FREE_CONTENT = _SECURITY.SecKeychainItemFreeContent
_SECURITY_KEYCHAIN_ITEM_FREE_CONTENT.argtypes = (
    _ctypes.c_void_p,
    _ctypes.c_void_p,
)
_SECURITY_KEYCHAIN_ITEM_FREE_CONTENT.restype = OS_RESULT

# https://developer.apple.com/documentation/corefoundation/1542359-cfdatacreate
CFDataCreate = _CORE.CFDataCreate
CFDataCreate.argtypes = [_ctypes.c_void_p, _ctypes.c_void_p, CFIndex]
CFDataCreate.restype = _ctypes.c_void_p

# https://developer.apple.com/documentation/_COREfoundation/1516782-cfdictionarycreate
CFDictionaryCreate = _CORE.CFDictionaryCreate
CFDictionaryCreate.argtypes = [
    _ctypes.c_void_p,
    _ctypes.c_void_p,
    _ctypes.c_void_p,
    CFIndex,
    _ctypes.c_void_p,
    _ctypes.c_void_p,
]
CFDictionaryCreate.restype = _ctypes.c_void_p

# https://developer.apple.com/documentation/_COREfoundation/1543330-cfdatagetbyteptr
CFDataGetBytePtr = _CORE.CFDataGetBytePtr
CFDataGetBytePtr.restype = _ctypes.c_void_p
CFDataGetBytePtr.argtypes = (_ctypes.c_void_p,)

# https://developer.apple.com/documentation/_COREfoundation/1541728-cfdatagetlength
CFDataGetLength = _CORE.CFDataGetLength
CFDataGetLength.argtypes = (_ctypes.c_void_p,)
CFDataGetLength.restype = _ctypes.c_int32

# https://developer.apple.com/documentation/_COREfoundation/1542182-cfnumbercreate
CFNumberCreate = _CORE.CFNumberCreate
CFNumberCreate.argtypes = [_ctypes.c_void_p, _ctypes.c_uint32, _ctypes.c_void_p]
CFNumberCreate.restype = _ctypes.c_void_p

# https://developer.apple.com/documentation/_COREfoundation/1542942-cfstringcreatewithcstring
CFStringCreateWithCString = _CORE.CFStringCreateWithCString
CFStringCreateWithCString.argtypes = [
    _ctypes.c_void_p,
    _ctypes.c_void_p,
    _ctypes.c_uint32,
]
CFStringCreateWithCString.restype = _ctypes.c_void_p

# https://developer.apple.com/documentation/_COREfoundation/1542721-cfstringgetcstring
CFStringGetCString = _CORE.CFStringGetCString
CFStringGetCString.argtypes = [
    CFStringRef,
    _ctypes.c_char_p,
    CFIndex,
    _ctypes.c_int,
]
CFStringGetCString.restype = _ctypes.c_bool

# https://developer.apple.com/documentation/_COREfoundation/1542853-cfstringgetlength
CFStringGetLength = _CORE.CFStringGetLength
CFStringGetLength.argtypes = [CFStringRef]
CFStringGetLength.restype = CFIndex

# https://developer.apple.com/documentation/security/1401659-secitemadd
SecItemAdd = _SECURITY.SecItemAdd
SecItemAdd.argtypes = [_ctypes.c_void_p, _ctypes.c_void_p]
SecItemAdd.restype = OS_RESULT

# https://developer.apple.com/documentation/security/1393617-secitemupdate
SecItemUpdate = _SECURITY.SecItemUpdate
SecItemUpdate.argtypes = [_ctypes.c_void_p, _ctypes.c_void_p]
SecItemUpdate.restype = OS_RESULT

# https://developer.apple.com/documentation/security/1398306-secitemcopymatching
SecItemCopyMatching = _SECURITY.SecItemCopyMatching
SecItemCopyMatching.argtypes = [_ctypes.c_void_p, _ctypes.c_void_p]
SecItemCopyMatching.restype = OS_RESULT


def createCFString(inputString):
    """Create a CFString. Needs input sanitization and error handling"""
    cfStr = CFStringCreateWithCString(
        None, inputString.encode("utf8"), kCFStringEncodingUTF8
    )
    return cfStr


def k_(s):
    return _ctypes.c_void_p.in_dll(_SECURITY, s)


def createCFDictionary(**kwargs):
    """Function to create the dictionary parameters"""
    return CFDictionaryCreate(
        None,
        (_ctypes.c_void_p * len(kwargs))(*[k_(k) for k in kwargs.keys()]),
        (_ctypes.c_void_p * len(kwargs))(
            *[createCFString(v) if isinstance(v, str) else v for v in kwargs.values()]
        ),
        len(kwargs),
        None,
        None,
    )


def getCFString(cfStr):
    """Get a CFString"""
    cfStrLen = CFStringGetLength(cfStr)  # Length of cfStr
    cfstr_x = (_ctypes.c_char * (cfStrLen * 4))()
    cfstrBuf = _ctypes.cast(cfstr_x, _ctypes.c_char_p)  # Create the CFString Buffer

    # CFStringGetCSString returns false if the conversion fails
    if not CFStringGetCString(cfStr, cfstrBuf, cfStrLen * 4, kCFStringEncodingUTF8):
        return None
    else:
        # Decode and return the string
        return cfstrBuf.value.decode("utf-8")


def cfDataToStr(data):
    """Extract a string from CFData"""
    return _ctypes.string_at(CFDataGetBytePtr(data), CFDataGetLength(data)).decode(
        "utf-8"
    )


def getSecErrorStr(resultCode):
    """Function to get the string representation of a security result code"""
    cfStringRef = _SECURITY_COPY_ERROR_MESSAGE_STRING(
        resultCode, None
    )  # Get the CFStringRef of the errStr
    errStr = getCFString(cfStringRef)
    _CORE_RELEASE(cfStringRef)
    return errStr


class Keychain(object):
    """Encapsulates the interactions with a particular MacOS Keychain."""

    def __init__(self, filename=None):
        # type: (str) -> None
        self._ref = _ctypes.c_void_p()

        if filename:
            filename = os.path.expanduser(filename)
            self._filename = filename.encode("utf-8")
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

        https://developer.apple.com/documentation/security/keychain_services/keychain_items/searching_for_keychain_items
        """

        cfDict = createCFDictionary(
            kSecClass=_ctypes.c_void_p.in_dll(_SECURITY, "kSecClassGenericPassword"),
            kSecMatchLimit=_ctypes.c_void_p.in_dll(_SECURITY, "kSecMatchLimit"),
            kSecAttrService=service,
            kSecAttrAccount=account_name,
            kSecReturnData=_ctypes.c_void_p.in_dll(_SECURITY, "kCFBooleanTrue"),
        )

        data = _ctypes.c_void_p()
        exit_status = SecItemCopyMatching(cfDict, _ctypes.byref(data))

        if exit_status:
            raise KeychainError(exit_status=exit_status)

        return cfDataToStr(data)

    def set_generic_password(self, service, account_name, value):
        # type: (str, str, str) -> None
        """Associate a password with a given service and account.

        :param service: The service to associate this password with.
        :param account_name: The account to associate this password with.
        :param value: The string that should be used as the password.

        https://developer.apple.com/documentation/security/keychain_services/keychain_items/adding_a_password_to_the_keychain
        """
        value = CFDataCreate(None, str.encode(value), len(value))

        queryUser = createCFDictionary(
            kSecClass=_ctypes.c_void_p.in_dll(_SECURITY, "kSecClassGenericPassword"),
            kSecMatchLimit=_ctypes.c_void_p.in_dll(_SECURITY, "kSecMatchLimit"),
            kSecAttrService=service,
            kSecAttrAccount=account_name,
        )

        find_exit_status = SecItemCopyMatching(queryUser, None)

        if not find_exit_status:
            updatePassAttr = createCFDictionary(kSecValueData=value)
            modify_exit_status = SecItemUpdate(queryUser, updatePassAttr)

            if modify_exit_status:
                raise KeychainError(exit_status=modify_exit_status)

        elif find_exit_status == KeychainError.ITEM_NOT_FOUND:
            addUser = createCFDictionary(
                kSecClass=_ctypes.c_void_p.in_dll(
                    _SECURITY, "kSecClassGenericPassword"
                ),
                kSecAttrService=service,
                kSecAttrAccount=account_name,
                kSecValueData=value,
            )

            add_exit_status = SecItemAdd(addUser, None)

            if add_exit_status:
                raise KeychainError(exit_status=add_exit_status)
        else:
            raise KeychainError(exit_status=find_exit_status)

    def get_internet_password(self, service, username):
        # type: (str, str) -> str
        """Fetches a password associated with a domain and username.
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
