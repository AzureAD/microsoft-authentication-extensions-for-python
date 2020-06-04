import logging
import os
import sys
import time

from portalocker import exceptions

from msal_extensions import FilePersistence, CrossPlatLock


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
    except exceptions.LockException as e:
        logging.warning("Unable to acquire lock %s", e)


_acquire_lock_and_write_to_cache(sys.argv[1], float(sys.argv[2]))

