import random

from PyQt5.Qt import pyqtSignal
from PyQt5.Qt import QThread, QObject
from subprocess import Popen, PIPE, STDOUT, CREATE_NO_WINDOW
import re
from core import is_debug, BASE_DIR
from time import time
import os
import time
from typing import Optional
from queue import Queue, Empty
from chiapos import Verifier, DiskProver
from utils.chia.hash import std_hash
from utils.chia.plotting.plot_tools import parse_plot_info
from utils import size_to_k


class FolderInfo(object):
    def __init__(self):
        super().__init__()
        self.folder = ''
        self.plots = []
        self.current_checking_plot = None

    def clear(self):
        self.plots.clear()
        self.current_checking_plot = None

    @property
    def plot_count(self):
        return len(self.plots)

    @property
    def checked_plot_count(self):
        count = 0
        for plot in self.plots:
            if plot.finish:
                count += 1
        return count

    @property
    def progress(self):
        if self.plot_count == 0:
            return 0
        return self.checked_plot_count * 100 / self.plot_count


class PlotInfo(object):
    def __init__(self, index):
        super().__init__()

        self.index = index
        self.folder_info: Optional[FolderInfo] = None
        self.prover: Optional[DiskProver] = None

        self.filename = ''
        self.path = ''
        self.k = ''
        self.fpk = ''
        self.ppk = ''
        self.contract = ''
        self.quality = ''
        self.status = ''
        self.finish = False
        self.success = False
        self.progress = 0


class PlotCheckWorker(QThread):
    signalFoundPlot = pyqtSignal(FolderInfo, PlotInfo)
    signalUpdateFolder = pyqtSignal(FolderInfo)
    signalUpdatePlot = pyqtSignal(PlotInfo)

    signalFinish = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(PlotCheckWorker, self).__init__()

        self.queue: Optional[Queue] = None
        self.folder_infos = []
        self.plots = []
        self.check_quality = False
        self.challenge_count = 30
        self.cancel = False

        if 'queue' in kwargs:
            self.queue: Queue = kwargs['queue']
        if 'folder_infos' in kwargs:
            self.folder_infos = kwargs['folder_infos']
        if 'plots' in kwargs:
            self.plots = kwargs['plots']
        if 'check_quality' in kwargs:
            self.check_quality = kwargs['check_quality']
        if 'challenge_count' in kwargs:
            self.challenge_count = kwargs['challenge_count']

    def run(self):
        if self.queue:
            self.run_queue(self.queue)
        elif self.folder_infos:
            self.run_folders(self.folder_infos)

    def run_queue(self, queue: Queue):
        while True:
            try:
                folder_infos = queue.get(False)
                self.run_folders(folder_infos)
            except Empty:
                break

    def run_folders(self, folder_infos):
        plots = []
        for folder_info in folder_infos:
            files = []
            try:
                files = os.listdir(folder_info.folder)
            except:
                pass

            index = 0
            for fn in files:
                index += 1
                plot = PlotInfo(index)
                plot.folder_info = folder_info
                plot.path = os.path.join(folder_info.folder, fn)
                plot.filename = fn
                plots.append(plot)
                folder_info.plots.append(plot)
                self.signalFoundPlot.emit(folder_info, plot)

        self.run_plots(plots)

    def run_plots(self, plots):
        for plot_info in plots:
            if self.cancel:
                break
            plot_info.status = '检查中'
            self.signalUpdatePlot.emit(plot_info)

            self.read_plot_info(plot_info)
            self.signalUpdatePlot.emit(plot_info)

            success = True
            status = '完成'
            if self.check_quality:
                success, quality = self.check_plot_quality(plot_info)
                if success:
                    plot_info.quality = f'{quality}'
                else:
                    if self.cancel:
                        status = '取消'
                    else:
                        status = '失败'
            plot_info.progress = 100
            plot_info.finish = True
            plot_info.status = status
            plot_info.success = success
            self.signalUpdatePlot.emit(plot_info)

    def read_plot_info(self, plot_info: PlotInfo):
        if is_debug():
            plot_info.fpk = 'xx'
            plot_info.ppk = 'xx'
            plot_info.contract = 'xx'
            plot_info.k = '32'
            time.sleep(0.1)
            return

        try:
            prover = DiskProver(plot_info.path)
            (
                is_pool_contract_puzzle_hash,
                pool_public_key_or_puzzle_hash,
                farmer_public_key,
                local_master_sk,
            ) = parse_plot_info(prover.get_memo())

            pool_public_key = ''
            pool_contract_puzzle_hash = ''

            if is_pool_contract_puzzle_hash:
                pool_contract_puzzle_hash = pool_public_key_or_puzzle_hash
            else:
                pool_public_key = pool_public_key_or_puzzle_hash

            plot_info.prover = prover
            plot_info.fpk = farmer_public_key
            plot_info.ppk = pool_public_key
            plot_info.contract = pool_contract_puzzle_hash
            plot_info.k = f'{size_to_k(os.path.getsize(plot_info.path))}'

            # return {
            #     'path': plot_path,
            #     'prover': prover,
            #     'farmer_public_key': farmer_public_key,
            #     'pool_public_key': pool_public_key,
            #     'pool_contract_puzzle_hash': pool_contract_puzzle_hash,
            #     'local_master_sk': local_master_sk,
            #     'plot_size': os.path.getsize(plot_path),
            # }
        except:
            pass

    def check_plot_quality(self, plot_info: PlotInfo):
        if is_debug():
            for i in range(self.challenge_count):
                if self.cancel:
                    return False, 0
                plot_info.progress = (i + 1) * 100 / self.challenge_count
                self.signalUpdatePlot.emit(plot_info)
                time.sleep(0.3)
            plot_info.progress = 100
            self.signalUpdatePlot.emit(plot_info)
            return True, random.choice([x / 10 for x in range(1, 19, 1)])

        v = Verifier()

        prover = plot_info.prover

        total_proofs = 0
        caught_exception: bool = False
        for i in range(self.challenge_count):
            challenge = std_hash(i.to_bytes(32, "big"))
            try:
                for index, quality_str in enumerate(prover.get_qualities_for_challenge(challenge)):
                    try:
                        proof = prover.get_full_proof(challenge, index, True)
                        total_proofs += 1
                        ver_quality_str = v.validate_proof(prover.get_id(), prover.get_size(), challenge, proof)
                        assert quality_str == ver_quality_str
                    except AssertionError as e:
                        caught_exception = True
            except KeyboardInterrupt:
                return False, 0
            except SystemExit:
                return False, 0
            except Exception as e:
                caught_exception = True
            if caught_exception is True:
                break
            if self.cancel:
                return False, 0
            plot_info.progress = (i+1) * 100 / self.challenge_count
            self.signalUpdatePlot.emit(plot_info)
        if total_proofs > 0 and caught_exception is False:
            plot_info.progress = 100
            self.signalUpdatePlot.emit(plot_info)

            return True, round(total_proofs/float(self.challenge_count), 4)
        return False, round(total_proofs/float(self.challenge_count), 4)


class PlotCheckManager(QThread):
    signalFoundPlot = pyqtSignal(FolderInfo, PlotInfo)
    signalUpdateFolder = pyqtSignal(FolderInfo)
    signalUpdatePlot = pyqtSignal(PlotInfo)
    signalFinish = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(PlotCheckManager, self).__init__(*args, **kwargs)
        self.queue = Queue()
        self.workers: [PlotCheckWorker] = []

        self.thread_count = 5
        self.folder_infos = []
        self.drivers = {}
        self.check_quality = False
        self.challenge_count = 30

    @property
    def working(self):
        return len(self.workers) != 0

    def clear(self):
        self.workers.clear()
        self.drivers.clear()
        self.queue.queue.clear()

    def start(self, *args, **kwargs):
        if 'thread_count' in kwargs:
            self.thread_count = kwargs['thread_count']
        if 'folder_infos' in kwargs:
            self.folder_infos = kwargs['folder_infos']
            for folder_info in self.folder_infos:
                driver = os.path.splitdrive(folder_info.folder)[0]
                if driver not in self.drivers:
                    self.drivers[driver] = []
                self.drivers[driver].append(folder_info)
        if 'check_quality' in kwargs:
            self.check_quality = kwargs['check_quality']
        if 'challenge_count' in kwargs:
            self.challenge_count = kwargs['challenge_count']

        super(PlotCheckManager, self).start()

    def run(self):
        for driver in self.drivers:
            self.queue.put(self.drivers[driver], False)

        for i in range(self.thread_count):
            worker = PlotCheckWorker(queue=self.queue, check_quality=self.check_quality,
                                     challenge_count=self.challenge_count)
            worker.signalFoundPlot.connect(self.signalFoundPlot)
            worker.signalUpdateFolder.connect(self.signalUpdateFolder)
            worker.signalUpdatePlot.connect(self.signalUpdatePlot)

            self.workers.append(worker)
            worker.start()

        for worker in self.workers:
            worker.wait()

        self.signalFinish.emit()
        self.workers.clear()

    def stop(self):
        for worker in self.workers:
            worker.cancel = True
        self.queue.queue.clear()
