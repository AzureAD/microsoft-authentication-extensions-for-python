import sys
import os
import time
import datetime
from msal_extensions import CrossPlatLock


def main(hold_time):
    # type: (datetime.timedelta) -> None
    """
    Grabs a lock from a well-known file in order to test the CrossPlatLock class across processes.
    :param hold_time: The approximate duration that this process should hold onto the lock.
    :return: None
    """
    pid = os.getpid()
    print('{} starting'.format(pid))
    with CrossPlatLock('./delete_me.lockfile'):
        print('{} has acquired the lock'.format(pid))
        time.sleep(hold_time.total_seconds())
        print('{} is releasing the lock'.format(pid))
    print('{} done.'.format(pid))


if __name__ == '__main__':
    lock_hold_time = datetime.timedelta(seconds=5)
    if len(sys.argv) > 1:
        hold_time = datetime.timedelta(seconds=int(sys.argv[1]))
    main(lock_hold_time)
