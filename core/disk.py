from PyQt5.Qt import pyqtSignal
from PyQt5.Qt import QThread
from queue import Queue
import psutil
import os
from datetime import datetime, timedelta
from utils.lock import RWlock
from config import get_config


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

    def updateSSDDriverSpaces(self, drivers):
        self.add_operation('updateSSDDriverSpaces', {
            'drivers': drivers,
        })

    def updateHDDDriverSpaces(self, drivers):
        self.add_operation('updateHDDDriverSpaces', {
            'drivers': drivers,
        })

    def updateTotalSpaces(self, drivers):
        self.add_operation('updateTotalSpaces', {
            'drivers': drivers,
        })

    def updateFolderPlotCount(self, folders):
        self.add_operation('updateFolderPlotCount', {
            'folders': folders,
        })

    def updatePlotTotalInfo(self, folders):
        self.add_operation('updatePlotTotalInfo', {
            'folders': folders,
        })

    def updateMiningPlotTotalInfo(self):
        config = get_config()

        folders = []

        if 'hdd_folders' in config:
            for folder_obj in config['hdd_folders']:
                if not folder_obj['mine']:
                    continue
                folder = folder_obj['folder']
                folders.append(folder)

        self.updatePlotTotalInfo(folders)

    def run(self):
        while True:
            op = self.queue.get()

            name = op['name']
            opt = op['opt']

            if name == 'updateSSDDriverSpaces' or name == 'updateHDDDriverSpaces':
                self.run_updateDriverSpaces(opt)
            elif name == 'updateTotalSpaces':
                self.run_updateTotalSpaces(opt)
            elif name == 'updatePlotTotalInfo':
                self.run_updatePlotTotalInfo(opt)
            elif name == 'updateFolderPlotCount':
                self.run_updateFolderPlotCount(opt)

            self.signalResult.emit(name, opt)

    def run_updateDriverSpaces(self, opt):
        drivers = opt['drivers']

        result = {}
        for driver in drivers:
            folder_usage = {'used': 0, 'free': 0, 'total': 0, 'percent': 0}

            try:
                usage = psutil.disk_usage(driver)
                folder_usage['used'] = usage.used
                folder_usage['free'] = usage.free
                folder_usage['total'] = usage.total
                folder_usage['percent'] = usage.percent

                set_disk_usage(driver, usage)
            except:
                pass

            # folder_usage['plots_info'] = self.get_folder_plots_info(driver)

            result[driver] = folder_usage

        opt['result'] = result

    def run_updateTotalSpaces(self, opt):
        drivers = opt['drivers']

        total_space = total_free = total_used = 0

        driver_count = 0
        total_size = 0
        total_count = 0
        yesterday_count = 0
        today_count = 0

        try:
            for driver in drivers:
                if os.path.exists(driver):
                    usage = psutil.disk_usage(driver)
                    total_space += usage.total
                    total_used += usage.used
                    total_free += usage.free

                    info = self.get_folder_plots_info(driver)
                    driver_count += 1
                    total_size += info['total_size']
                    total_count += info['total_count']
                    yesterday_count += info['yesterday_count']
                    today_count += info['today_count']
        except:
            pass

        opt['result'] = {
            'driver_count': driver_count,
            'total_space': total_space,
            'total_free': total_free,
            'total_used': total_used,
            'plots_info': {
                'total_size': total_size,
                'total_count': total_count,
                'yesterday_count': yesterday_count,
                'today_count': today_count,
            },
        }

    def run_updatePlotTotalInfo(self, opt):
        folders = opt['folders']

        total_size = 0
        total_count = 0
        yesterday_count = 0
        today_count = 0

        for folder in folders:
            info = self.get_folder_plots_info(folder)
            if info is None:
                continue
            total_size += info['total_size']
            total_count += info['total_count']
            yesterday_count += info['yesterday_count']
            today_count += info['today_count']

        opt['result'] = {
            'total_size': total_size,
            'total_count': total_count,
            'yesterday_count': yesterday_count,
            'today_count': today_count,
        }

    def run_updateFolderPlotCount(self, opt):
        folders = opt['folders']

        folders_plot_info = {}
        for folder in folders:
            info = self.get_folder_plots_info(folder)
            if info is None:
                continue
            folders_plot_info[folder] = {
                'total_count': info['total_count'],
                'total_size': info['total_size']
            }

        opt['result'] = {
            'folders_plot_info': folders_plot_info
        }

    def get_folder_plots_info(self, folder):
        total_size = 0
        total_count = 0
        yesterday_count = 0
        today_count = 0

        today = datetime.now()
        yesterday = datetime.now() - timedelta(days=1)

        try:
            if os.path.exists(folder):
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

        return {
            'total_size': total_size,
            'total_count': total_count,
            'yesterday_count': yesterday_count,
            'today_count': today_count,
        }


disk_operation = DiskOperation()
