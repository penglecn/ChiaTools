import os
import random
from config import get_config
from utils import get_k_size


class HDDFolders(object):
    def __init__(self):
        config = get_config()
        self.drivers = {}

        if 'hdd_folders' in config:
            hdd_folders_obj = config['hdd_folders']

            for folder_obj in hdd_folders_obj:
                folder = folder_obj['folder']
                mine = folder_obj['mine']
                new_plot = folder_obj['new_plot']
                driver, _ = os.path.splitdrive(folder)
                if driver not in self.drivers:
                    self.drivers[driver] = []
                self.drivers[driver].append(folder_obj)

    def get_drivers(self):
        drivers = []
        for driver in self.drivers:
            drivers.append(driver)
        return drivers

    def get_driver_folders(self, driver, except_folder='', mine=None, new_plot=None, have_plots=None):
        if driver not in self.drivers:
            return []

        folders_obj = self.drivers[driver]
        folders = []

        for folder_obj in folders_obj:
            folder = folder_obj['folder']
            if except_folder and folder == except_folder:
                continue
            if mine is not None and folder_obj['mine'] != mine:
                continue
            if new_plot is not None and folder_obj['new_plot'] != new_plot:
                continue
            if have_plots is not None:
                _have_plots = False
                try:
                    for fn in os.listdir(folder):
                        if fn.endswith('.plot'):
                            _have_plots = True
                            break
                except:
                    pass
                if have_plots != _have_plots:
                    continue
            folders.append(folder)

        return folders

    def delete_for_plot_in_folder(self, folder, k=32):
        k_size = get_k_size(k)
        folder_files = []
        try:
            folder_files = os.listdir(folder)
        except:
            pass

        deleted_size = 0
        for fn in folder_files:
            if fn.endswith('.plot'):
                plot_fn = os.path.join(folder, fn)
                try:
                    plot_size = os.path.getsize(plot_fn)
                    os.remove(plot_fn)
                    deleted_size += plot_size
                    if deleted_size > k_size:
                        return True, deleted_size
                except:
                    pass

        return False, deleted_size

    def delete_for_plot(self, k=32):
        k_size = get_k_size(k)
        drivers = self.get_drivers()
        random.shuffle(drivers)

        for driver in drivers:
            for folder_obj in self.drivers[driver]:
                if folder_obj['new_plot']:
                    continue
                folder = folder_obj['folder']
                if not self.is_folder_have_old_plot(folder, k):
                    continue
                _, deleted_size = self.delete_for_plot_in_folder(folder, k)
                if deleted_size > k_size:
                    return True, folder

        return False, ''

    def is_folder_have_old_plot(self, hdd_folder, k=32):
        for_k_size = get_k_size(k)

        for driver in self.drivers:
            for folder_obj in self.drivers[driver]:
                if folder_obj['folder'] == hdd_folder:
                    old_size = 0
                    if folder_obj['new_plot']:
                        return False
                    try:
                        for fn in os.listdir(hdd_folder):
                            if fn.endswith('.plot'):
                                fp = os.path.join(hdd_folder, fn)
                                old_size += os.path.getsize(fp)
                                if old_size >= for_k_size:
                                    return True
                    except:
                        pass
                    return False
        return False

    def is_driver_have_old_plot(self, driver, k=32):
        for_k_size = get_k_size(k)

        for folder_obj in self.drivers[driver]:
            old_size = 0

            if folder_obj['new_plot']:
                continue

            folder = folder_obj['folder']
            try:
                for fn in os.listdir(folder):
                    if fn.endswith('.plot'):
                        fp = os.path.join(folder, fn)
                        old_size += os.path.getsize(fp)
                        if old_size >= for_k_size:
                            return True
            except:
                pass
        return False
