"""
Usage: cache_file_generator.py cache_file_path sleep_interval

This is a console application which is to be used for cross-platform lock performance testing.
The app will acquire lock for the cache file, log the process id and then release the lock.

It takes in two arguments - cache file path and the sleep interval.
The cache file path is the path of cache file.
The sleep interval is the time in seconds for which the lock is held by a process.
"""

import logging
import os
import sys
import time

from msal_extensions import FilePersistence, CrossPlatLock, LockError


print("Testing with {}".format(CrossPlatLock))


def _acquire_lock_and_write_to_cache(cache_location, sleep_interval):
    cache_accessor = FilePersistence(cache_location)
    lock_file_path = cache_accessor.get_location() + ".lockfile"
    try:
        with CrossPlatLock(lock_file_path):
            data = cache_accessor.load()
            if data is None:
                data = ""
            data += "< " + str(os.getpid()) + "\n"
            time.sleep(sleep_interval)
            data += "> " + str(os.getpid()) + "\n"
            cache_accessor.save(data)
    except LockError as e:
        logging.warning("Unable to acquire lock %s", e)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(0)
    _acquire_lock_and_write_to_cache(sys.argv[1], float(sys.argv[2]))

