"""Provides auxiliary functionality to the `msal` package."""
__version__ = "1.2.0"  # Note: During/after release, copy this number to Dockerfile

from .persistence import (
    FilePersistence,
    build_encrypted_persistence,
    FilePersistenceWithDataProtection,
    KeychainPersistence,
    LibsecretPersistence,
    )
from .token_cache import PersistedTokenCache, CrossPlatLock, LockError

