import multiprocessing
import os
import shutil
import tempfile

import pytest

from .cache_file_generator import _acquire_lock_and_write_to_cache


@pytest.fixture
def temp_location():
    test_folder = tempfile.mkdtemp(prefix="test_persistence_roundtrip")
    yield os.path.join(test_folder, 'persistence.bin')
    shutil.rmtree(test_folder, ignore_errors=True)


def _validate_result_in_cache(cache_location):
    with open(cache_location) as handle:
        data = handle.read()
    prev_process_id = None
    count = 0
    for line in data.split("\n"):
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


def test_lock_for_normal_workload(temp_location):
    num_of_processes = 4
    sleep_interval = 0.1
    _run_multiple_processes(num_of_processes, temp_location, sleep_interval)
    count = _validate_result_in_cache(temp_location)
    assert count == num_of_processes * 2, "Should not observe starvation"


def test_lock_for_high_workload(temp_location):
    num_of_processes = 80
    sleep_interval = 0
    _run_multiple_processes(num_of_processes, temp_location, sleep_interval)
    count = _validate_result_in_cache(temp_location)
    assert count <= num_of_processes * 2, "Starvation or not, we should not observe garbled payload"


def test_lock_for_timeout(temp_location):
    num_of_processes = 30
    sleep_interval = 1
    _run_multiple_processes(num_of_processes, temp_location, sleep_interval)
    count = _validate_result_in_cache(temp_location)
    assert count < num_of_processes * 2, "Should observe starvation"

