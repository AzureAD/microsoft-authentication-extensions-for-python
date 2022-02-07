"""Provides auxiliary functionality to the `msal` package."""
__version__ = "0.3.1"

from .persistence import (
    FilePersistence,
    FilePersistenceWithDataProtection,
    KeychainPersistence,
    LibsecretPersistence,
    )
from .cache_lock import CrossPlatLock
from .token_cache import PersistedTokenCache

