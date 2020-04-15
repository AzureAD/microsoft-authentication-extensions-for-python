"""A generic persistence layer, optionally encrypted on Windows, OSX, and Linux.

Should a certain encryption is unavailable, exception will be raised at run-time,
rather than at import time.

By successfully creating and using a certain persistence object,
app developer would naturally know whether the data are protected by encryption.
"""
import abc
import os
import errno
try:
    from pathlib import Path  # Built-in in Python 3
except:
    from pathlib2 import Path  # An extra lib for Python 2


try:
    ABC = abc.ABC
except AttributeError:  # Python 2.7, abc exists, but not ABC
    ABC = abc.ABCMeta("ABC", (object,), {"__slots__": ()})  # type: ignore


def _mkdir_p(path):
    """Creates a directory, and any necessary parents.

    This implementation based on a Stack Overflow question that can be found here:
    https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python

    If the path provided is an existing file, this function raises an exception.
    :param path: The directory name that should be created.
    """
    if not path:
        return  # NO-OP
    try:
        os.makedirs(path)
    except OSError as exp:
        if exp.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class BasePersistence(ABC):
    """An abstract persistence defining the common interface of this family"""

    is_encrypted = False  # Default to False. To be overridden by sub-classes.

    @abc.abstractmethod
    def save(self, content):
        # type: (str) -> None
        """Save the content into this persistence"""
        raise NotImplementedError

    @abc.abstractmethod
    def load(self):
        # type: () -> str
        """Load content from this persistence"""
        raise NotImplementedError

    @abc.abstractmethod
    def time_last_modified(self):
        """Get the last time when this persistence has been modified"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_location(self):
        """Return the file path which this persistence stores (meta)data into"""
        raise NotImplementedError


class FilePersistence(BasePersistence):
    """A generic persistence, storing data in a plain-text file"""

    def __init__(self, location):
        if not location:
            raise ValueError("Requires a file path")
        self._location = os.path.expanduser(location)
        _mkdir_p(os.path.dirname(self._location))

    def save(self, content):
        # type: (str) -> None
        """Save the content into this persistence"""
        with open(self._location, 'w+') as handle:
            handle.write(content)

    def load(self):
        # type: () -> str
        """Load content from this persistence"""
        with open(self._location, 'r') as handle:
            return handle.read()

    def time_last_modified(self):
        return os.path.getmtime(self._location)

    def touch(self):
        """To touch this file-based persistence without writing content into it"""
        Path(self._location).touch()  # For os.path.getmtime() to work

    def get_location(self):
        return self._location


class FilePersistenceWithDataProtection(FilePersistence):
    """A generic persistence with data stored in a file,
    protected by Win32 encryption APIs on Windows"""
    is_encrypted = True

    def __init__(self, location, entropy=''):
        """Initialization could fail due to unsatisfied dependency"""
        # pylint: disable=import-outside-toplevel
        from .windows import WindowsDataProtectionAgent
        self._dp_agent = WindowsDataProtectionAgent(entropy=entropy)
        super(FilePersistenceWithDataProtection, self).__init__(location)

    def save(self, content):
        super(FilePersistenceWithDataProtection, self).save(
            self._dp_agent.protect(content))

    def load(self):
        return self._dp_agent.unprotect(
            super(FilePersistenceWithDataProtection, self).load())


class KeychainPersistence(BasePersistence):
    """A generic persistence with data stored in,
    and protected by native Keychain libraries on OSX"""
    is_encrypted = True

    def __init__(self, signal_location, service_name, account_name):
        """Initialization could fail due to unsatisfied dependency.

        :param signal_location: See :func:`persistence.LibsecretPersistence.__init__`
        """
        if not (service_name and account_name):  # It would hang on OSX
            raise ValueError("service_name and account_name are required")
        from .osx import Keychain  # pylint: disable=import-outside-toplevel
        self._file_persistence = FilePersistence(signal_location)  # Favor composition
        self._Keychain = Keychain  # pylint: disable=invalid-name
        self._service_name = service_name
        self._account_name = account_name

    def save(self, content):
        with self._Keychain() as locker:
            locker.set_generic_password(
                self._service_name, self._account_name, content)
        self._file_persistence.touch()  # For time_last_modified()

    def load(self):
        with self._Keychain() as locker:
            return locker.get_generic_password(
                self._service_name, self._account_name)

    def time_last_modified(self):
        return self._file_persistence.time_last_modified()

    def get_location(self):
        return self._file_persistence.get_location()


class LibsecretPersistence(BasePersistence):
    """A generic persistence with data stored in,
    and protected by native libsecret libraries on Linux"""
    is_encrypted = True

    def __init__(self, signal_location, schema_name, attributes, **kwargs):
        """Initialization could fail due to unsatisfied dependency.

        :param string signal_location:
            Besides saving the real payload into encrypted storage,
            this class will also touch this signal file.
            Applications may listen a FileSystemWatcher.Changed event for reload.
            https://docs.microsoft.com/en-us/dotnet/api/system.io.filesystemwatcher.changed?view=netframework-4.8#remarks
        :param string schema_name: See :func:`libsecret.LibSecretAgent.__init__`
        :param dict attributes: See :func:`libsecret.LibSecretAgent.__init__`
        """
        # pylint: disable=import-outside-toplevel
        from .libsecret import (  # This uncertain import is deferred till runtime
            LibSecretAgent, trial_run)
        trial_run()
        self._agent = LibSecretAgent(schema_name, attributes, **kwargs)
        self._file_persistence = FilePersistence(signal_location)  # Favor composition

    def save(self, content):
        if self._agent.save(content):
            self._file_persistence.touch()  # For time_last_modified()

    def load(self):
        return self._agent.load()

    def time_last_modified(self):
        return self._file_persistence.time_last_modified()

    def get_location(self):
        return self._file_persistence.get_location()

# We could also have a KeyringPersistence() which can then be used together
# with a FilePersistence to achieve
#  https://github.com/AzureAD/microsoft-authentication-extensions-for-python/issues/12
# But this idea is not pursued at this time.

