"""Provides auxiliary functionality to the `msal` package."""
__version__ = "1.0.0"

from .persistence import (
    FilePersistence,
    build_encrypted_persistence,
    FilePersistenceWithDataProtection,
    KeychainPersistence,
    LibsecretPersistence,
    )
try:
    from .cache_lock import CrossPlatLock, LockError  # It needs portalocker
except ImportError:
    from .filelock import CrossPlatLock, LockError
from .token_cache import PersistedTokenCache

