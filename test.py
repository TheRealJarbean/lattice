from PySide6.QtCore import QMutex, QMutexLocker

def bad_lock(aLock):
    try:
        locker = QMutexLocker(aLock)
        print("Locked")
        raise RuntimeError("Test exception")

        return "Should not get here"
    
    except Exception as e:
        return

def good_lock(aLock):
    try:
        with QMutexLocker(aLock):
            print("Locked")
            raise RuntimeError("Test exception")

        return "Should not get here"

    except Exception as e:
        return

lock = QMutex()

bad_lock(lock)
print(lock.tryLock())
# False

lock.unlock()

good_lock(lock)
print(lock.tryLock())