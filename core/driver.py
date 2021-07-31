import os
import random

import core
from config import get_config
from utils import get_k_size, size_to_k, size_to_k32_count


class HDDFolders(object):
    def __init__(self):
        config = get_config()
        self.drivers = {}
        self.old_plot_folders = []
        self.new_plot_folders = []

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

                if new_plot:
                    self.new_plot_folders.append(folder)
                else:
                    self.old_plot_folders.append(folder)

    def is_old_plot_folder(self, folder):
        return folder in self.old_plot_folders

    def is_new_plot_folder(self, folder):
        return folder in self.new_plot_folders

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

    def delete_for_plot_in_folder(self, folder, need_size):
        need_count = size_to_k32_count(need_size)

        folder_files = []
        try:
            folder_files = os.listdir(folder)
        except:
            pass

        deleted_size = 0
        deleted_count = 0
        for fn in folder_files:
            if fn.endswith('.plot'):
                plot_fn = os.path.join(folder, fn)
                try:
                    plot_size = os.path.getsize(plot_fn)
                    if plot_size == 0 and core.is_debug():
                        plot_size = get_k_size(32)

                    k32_plot_count = size_to_k32_count(plot_size)

                    os.remove(plot_fn)
                    deleted_size += plot_size
                    deleted_count += k32_plot_count
                    if deleted_count >= need_count:
                        return True, deleted_size
                except:
                    pass

        return False, deleted_size

    def free_space_for_plot_in_driver(self, driver, need_size):
        if driver not in self.drivers:
            return False, ''

        need_count = size_to_k32_count(need_size)

        deleted_count = 0
        for folder_obj in self.drivers[driver]:
            if folder_obj['new_plot']:
                continue

            folder = folder_obj['folder']

            if not self.is_folder_have_plot(folder, need_size):
                continue

            _, deleted_size = self.delete_for_plot_in_folder(folder, need_size=need_size)

            deleted_count += size_to_k32_count(deleted_size)

            if deleted_count >= need_count:
                return True, folder

        return False, ''

    def get_driver_old_folder(self, driver):
        if driver not in self.drivers:
            return ''
        for folder_obj in self.drivers[driver]:
            if not folder_obj['new_plot']:
                return folder_obj['folder']
        return ''

    def get_driver_new_folder(self, driver):
        if driver not in self.drivers:
            return ''
        for folder_obj in self.drivers[driver]:
            if folder_obj['new_plot']:
                return folder_obj['folder']
        return ''

    def is_driver_have_old_and_new_folders(self, driver):
        if driver not in self.drivers:
            return False

        have_old = False
        have_new = False
        for folder_obj in self.drivers[driver]:
            if folder_obj['new_plot']:
                have_new = True
            else:
                have_old = True

        return have_old and have_new

    def is_folder_have_plot(self, folder, need_size):
        old_k32_count = 0

        need_count = size_to_k32_count(need_size)

        try:
            for fn in os.listdir(folder):
                if fn.endswith('.plot'):
                    fp = os.path.join(folder, fn)
                    plot_size = os.path.getsize(fp)
                    if plot_size == 0 and core.is_debug():
                        plot_size = get_k_size(32)

                    k32_plot_count = size_to_k32_count(plot_size)

                    old_k32_count += k32_plot_count
                    if old_k32_count >= need_count:
                        return True
        except:
            pass
        return False

    def is_driver_have_old_plot(self, driver, need_size):
        if driver not in self.drivers:
            return False

        need_count = size_to_k32_count(need_size)

        plot_count = 0
        for folder_obj in self.drivers[driver]:
            if folder_obj['new_plot']:
                continue

            folder = folder_obj['folder']
            try:
                for fn in os.listdir(folder):
                    if fn.endswith('.plot'):
                        fp = os.path.join(folder, fn)
                        plot_size = os.path.getsize(fp)
                        if plot_size == 0 and core.is_debug():
                            plot_size = get_k_size(32)

                        plot_count += size_to_k32_count(plot_size)

                        if plot_count >= need_count:
                            return True
            except:
                pass
        return False
