import multiprocessing
import threading
import time
from msal_extensions import FilePersistence, CrossPlatLock


def validate_thread_locking_file(num):
    with open("C:/Users/abpati/Desktop/test/lockfilelog.txt") as handle:
        data = handle.read()
    time_list = []
    for line in data.split("\n"):
        start, end = line.split("-")
        time_list.append([start, end])
    if len(time_list) != num:
        print("Threads count dont match ")
        return
    time_list.sort()
    prev = None
    for interval in time_list:
        start, end = interval
        if start > end:
            print("Intervals start bigger than end")
            return
        if prev:
            if start < prev:
                print("overlapping")
        prev = start
    print("success")
    return


def validate_result_in_cache(num):
    with open("C:/Users/abpati/Desktop/test/msal.cache") as handle:
        data = handle.read()
    prev_tag= None
    prev_proc_id = None
    count = 0
    for line in data.split(("\n")):
        tag, proc_id = line.split(" ")
        if tag == '<':
            if '<' == prev_tag:
                print("Failed")
                return
        elif tag == '>':
            count+=1
            if '<' != prev_tag or (not prev_proc_id == proc_id):
                print("Failed")
                return
        else:
            print("Unexpected Token")
        prev_proc_id = proc_id
        prev_tag = tag
    if ">" != prev_tag:
        print("Failed")
        return
    if count != num:
        print("Failed")
        return
    print("sucess")


def do_something(tid):
    lock_intervals_file_path = "C:/Users/abpati/Desktop/test/lockfilelog.txt"
    lock_file_path = "C:/Users/abpati/Desktop/test/msal.cache.lockfile"
    cache_accessor = FilePersistence("C:/Users/abpati/Desktop/test/msal.cache")
    with CrossPlatLock(lock_file_path, lock_intervals_file_path):
        thr = str(tid)
        data = cache_accessor.load()
        if data is None:
            data = ""
        data += "< " + thr + "\n"
        time.sleep(0.1)
        data += "> " + thr + "\n"
        cache_accessor.save(data)


def multiple_threads():
    threads = []
    num_of_threads = 30
    for i in range(num_of_threads):
        t = threading.Thread(target=do_something, args=(i,))
        threads.append(t)

    for i in threads:
        i.start()

    for i in threads:
        i.join()
    validate_thread_locking_file(num_of_threads)
    validate_result_in_cache(num_of_threads)


def multiple_process():
    processes = []
    num_of_processes = 20
    for i in range(num_of_processes):
        t = multiprocessing.Process(target=do_something, args=(i,))
        processes.append(t)

    for i in processes:
        i.start()

    for i in processes:
        i.join()
    validate_thread_locking_file(num_of_processes)
    validate_result_in_cache(num_of_processes)


multiple_threads()
multiple_process()