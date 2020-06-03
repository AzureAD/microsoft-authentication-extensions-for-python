import sys

from test_cache_lock_file_perf import _acquire_lock_and_write_to_cache

_acquire_lock_and_write_to_cache(sys.argv[1], float(sys.argv[2]))

