import logging
import multiprocessing
import os
import time

import pytest

from msal_extensions import FilePersistence, CrossPlatLock


@pytest.fixture
def cache_location():
    path_to_script = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(path_to_script, "msal.cache")


def _validate_result_in_cache(expected_entry_count, cache_location):
    with open(cache_location) as handle:
        data = handle.read()
    prev_process_id = None
    count = 0
    for line in data.split(("\n")):
        if line:
            count += 1
            tag, process_id = line.split(" ")
            if prev_process_id is not None:
                assert process_id == prev_process_id, "Process overlap found"
                assert tag == '>', "Process overlap_found"
                prev_process_id = None
            else:
                assert tag == '<', "Opening bracket not found"
                prev_process_id = process_id

    assert count <= expected_entry_count * 2, "File content corrupted"
    if count < expected_entry_count * 2:
        logging.warning("Starvation detected")


def _acquire_lock_and_write_to_cache(cache_location, sleep_interval=0):
    cache_accessor = FilePersistence(cache_location)
    lock_file_path = cache_accessor.get_location() + ".lockfile"
    with CrossPlatLock(lock_file_path):
        data = cache_accessor.load()
        if data is None:
            data = ""
        data += "< " + str(os.getpid()) + "\n"
        time.sleep(sleep_interval)
        data += "> " + str(os.getpid()) + "\n"
        cache_accessor.save(data)


def _run_multiple_processes(no_of_processes, cache_location, sleep_interval):
    open(cache_location, "w+")
    processes = []
    for i in range(no_of_processes):
        t = multiprocessing.Process(
            target=_acquire_lock_and_write_to_cache,
            args=(cache_location, sleep_interval))
        processes.append(t)

    for process in processes:
        process.start()

    for process in processes:
        process.join()


def test_multiple_processes_without_timeout_exception(cache_location):
    num_of_processes = 100
    sleep_interval = 0
    _run_multiple_processes(num_of_processes, cache_location, sleep_interval)
    _validate_result_in_cache(num_of_processes, cache_location)
    os.remove(cache_location)


def test_multiple_processes_with_timeout_exception_raised(cache_location):
    num_of_processes = 6
    sleep_interval = 1
    with pytest.raises(Exception):
        assert _run_multiple_processes(
            num_of_processes, cache_location, sleep_interval)
    os.remove(cache_location)

