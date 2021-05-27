from PyQt5.Qt import pyqtSignal
from PyQt5.Qt import QThread
from queue import Queue
import psutil
import os
from datetime import datetime, timedelta
from utils.lock import RWlock


__disk_usage_cache = {}
__disk_cache_lock = RWlock()


def set_disk_usage(folder, usage):
    __disk_cache_lock.write_acquire()
    __disk_usage_cache[folder] = usage
    __disk_cache_lock.write_release()


def get_disk_usage(folder):
    __disk_cache_lock.read_acquire()
    if folder not in __disk_usage_cache:
        __disk_cache_lock.read_release()
        try:
            usage = psutil.disk_usage(folder)
            set_disk_usage(folder, usage)
        except:
            return None
    else:
        usage = __disk_usage_cache[folder]
        __disk_cache_lock.read_release()

    return usage


class DiskOperation(QThread):
    signalResult = pyqtSignal(str, dict)

    def __init__(self):
        super(DiskOperation, self).__init__()
        self.queue = Queue()

    def add_operation(self, name, opt):
        self.queue.put({
            'name': name,
            'opt': opt,
        })

    def run(self):
        while True:
            op = self.queue.get()

            name = op['name']
            opt = op['opt']

            if name == 'updateDriverSpaces':
                self.run_updateDriverSpaces(opt)
            elif name == 'updateTotalSpaces':
                self.run_updateTotalSpaces(opt)
            elif name == 'updateTotalGB':
                self.run_updateTotalGB(opt)

            self.signalResult.emit(name, opt)

    def run_updateDriverSpaces(self, opt):
        folders = opt['folders']

        result = {}
        for folder in folders:
            folder_usage = {'used': 0, 'free': 0, 'total': 0, 'percent': 0}

            try:
                usage = psutil.disk_usage(folder)
                folder_usage['used'] = usage.used
                folder_usage['free'] = usage.free
                folder_usage['total'] = usage.total
                folder_usage['percent'] = usage.percent

                set_disk_usage(folder, usage)
            except:
                pass

            result[folder] = folder_usage

        opt['result'] = result

    def run_updateTotalSpaces(self, opt):
        folders = opt['folders']

        total_space = total_free = total_used = 0

        try:
            for folder in folders:
                if os.path.exists(folder):
                    usage = psutil.disk_usage(folder)
                    total_space += usage.total
                    total_used += usage.used
                    total_free += usage.free
        except:
            pass

        result = {'total_space': total_space, 'total_free': total_free, 'total_used': total_used}

        opt['result'] = result

    def run_updateTotalGB(self, opt):
        folders = opt['folders']

        total_size = 0
        total_count = 0
        yesterday_count = 0
        today_count = 0

        today = datetime.now()
        yesterday = datetime.now() - timedelta(days=1)

        try:
            for folder in folders:
                if not os.path.exists(folder):
                    continue

                files = os.listdir(folder)
                for f in files:
                    if not f.endswith('.plot'):
                        continue
                    file = os.path.join(folder, f)
                    if os.path.isfile(file):
                        total_size += os.path.getsize(file)
                        total_count += 1

                        mtime = os.path.getmtime(file)
                        dt = datetime.fromtimestamp(mtime)
                        if dt.year == yesterday.year and dt.month == yesterday.month and dt.day == yesterday.day:
                            yesterday_count += 1
                        if dt.year == today.year and dt.month == today.month and dt.day == today.day:
                            today_count += 1
        except:
            pass

        result = {'total_size': total_size, 'total_count': total_count, 'yesterday_count': yesterday_count, 'today_count': today_count}

        opt['result'] = result
