"""Provides a mechanism for not competing with other processes interacting with an MSAL cache."""
import os
import sys
import logging

import portalocker  # pylint: disable=import-error


logger = logging.getLogger(__name__)


LockError = portalocker.exceptions.LockException


class CrossPlatLock(object):
    """Offers a mechanism for waiting until another process is finished interacting with a shared
    resource. This is specifically written to interact with a class of the same name in the .NET
    extensions library.

    Fix: Use blocking LOCK_EX (no LOCK_NB) and never delete the lockfile.
    The original design had two races:
    1. LOCK_NB caused 300+ concurrent processes to bypass the lock (LockError raised instead of
       waiting), allowing concurrent writes to the shared .tmp file.
    2. Deleting the lockfile after releasing let another process create a new inode at the same
       path, so two processes could each hold "exclusive" locks on different inodes simultaneously.
    Both races caused the shared .tmp file to receive concurrent interleaved writes, producing
    JSONDecodeError("Extra data") in the cache.
    """
    def __init__(self, lockfile_path):
        self._lockpath = lockfile_path
        self._lock = portalocker.Lock(
            lockfile_path,
            # Use append mode: opens without truncating, creates file if absent.
            # Never truncate the lockfile — that would corrupt another holder's fd.
            mode='a',
            # Use blocking LOCK_EX only (no LOCK_NB).
            # With LOCK_NB, all but one of 300 concurrent processes would raise LockError
            # immediately instead of waiting, bypassing the critical section entirely.
            flags=portalocker.LOCK_EX,
            buffering=0,
        )

    def __enter__(self):
        pid = os.getpid()
        file_handle = self._lock.__enter__()
        logger.debug("Process %d acquired token cache lock", pid)
        return file_handle

    def __exit__(self, *args):
        # Release the lock but leave the lockfile on disk.
        # Deleting + recreating the file changes its inode, which breaks the POSIX guarantee
        # that fcntl locks are per-(process, inode) pair — two processes can then each hold
        # an "exclusive" lock on different inodes of the same path simultaneously.
        self._lock.__exit__(*args)
        logger.debug("Process %d released token cache lock", os.getpid())
