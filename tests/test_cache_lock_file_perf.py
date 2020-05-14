import multiprocessing
import os
import time

from msal_extensions import FilePersistence, CrossPlatLock


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

    assert count == expected_entry_count*2, "No of processes don't match"


def _acquire_lock_and_write_to_cache(cache_location, sleep_interval=1):
    cache_accessor = FilePersistence(cache_location)
    lock_file_path = cache_accessor.get_location() + ".lockfile"
    with CrossPlatLock(lock_file_path, timeout=90):
        data = cache_accessor.load()
        if data is None:
            data = ""
        data += "< " + str(os.getpid()) + "\n"
        time.sleep(sleep_interval)
        data += "> " + str(os.getpid()) + "\n"
        cache_accessor.save(data)


def test_multiple_process():
    path_to_script = os.path.dirname(os.path.abspath(__file__))
    cache_location = os.path.join(path_to_script, "msal.cache")
    open(cache_location, "w+")
    processes = []
    num_of_processes = 5
    for i in range(num_of_processes):
        t = multiprocessing.Process(
            target=_acquire_lock_and_write_to_cache,
            args=(cache_location,))
        processes.append(t)

    for i in processes:
        i.start()

    for i in processes:
        i.join()
    _validate_result_in_cache(num_of_processes, cache_location)
    os.remove(cache_location)
