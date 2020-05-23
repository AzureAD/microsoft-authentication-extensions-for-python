import logging
import multiprocessing
import os
import time

from portalocker import exceptions
import pytest

from msal_extensions import FilePersistence, CrossPlatLock


@pytest.fixture
def cache_location():
    path_to_script = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(path_to_script, str(os.getpid())+"msal.cache")


def _validate_result_in_cache(cache_location):
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
    return count


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
        logging.warning("Timeout occured %s", e)


def _run_multiple_processes(no_of_processes, cache_location, sleep_interval):
    open(cache_location, "w+")
    processes = []
    for i in range(no_of_processes):
        process = multiprocessing.Process(
            target=_acquire_lock_and_write_to_cache,
            args=(cache_location, sleep_interval))
        processes.append(process)

    for process in processes:
        process.start()

    for process in processes:
        process.join()


def test_lock_for_normal_workload(cache_location):
    num_of_processes = 4
    sleep_interval = 0.1
    _run_multiple_processes(num_of_processes, cache_location, sleep_interval)
    count = _validate_result_in_cache(cache_location)
    os.remove(cache_location)
    assert count == num_of_processes * 2, "Should not observe starvation"


def test_lock_for_high_workload(cache_location):
    num_of_processes = 20
    sleep_interval = 0
    _run_multiple_processes(num_of_processes, cache_location, sleep_interval)
    count = _validate_result_in_cache(cache_location)
    os.remove(cache_location)
    assert count <= num_of_processes * 2, "Should observe starvation"


def test_lock_for_timeout(cache_location):
    num_of_processes = 10
    sleep_interval = 1
    _run_multiple_processes(num_of_processes, cache_location, sleep_interval)
    count = _validate_result_in_cache(cache_location)
    os.remove(cache_location)
    assert count < num_of_processes * 2, "Should observe starvation"

