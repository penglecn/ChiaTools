from datetime import datetime
from PyQt5.Qt import pyqtSignal
from PyQt5.Qt import QThread, QObject
import time
import os
from subprocess import Popen, PIPE, CREATE_NO_WINDOW
import core
from core import BASE_DIR, is_debug
import re
import shutil
import psutil
import pickle
import platform
from config import get_config
import threading


class PlotTask(QObject):
    signalUpdateTask = pyqtSignal(object, object)
    signalMakingPlot = pyqtSignal(object, object)
    signalNewPlot = pyqtSignal(object, object)

    def __init__(self, *args, **kwargs):
        super(PlotTask, self).__init__(*args, **kwargs)

        self.running = False
        self.phase = 1

        self.fpk = ''
        self.ppk = ''
        self.ssd_folder = ''
        self.hdd_folder = ''
        self.temporary_folder = ''
        self.number_of_thread = 0
        self.memory_size = 0
        self.delay_seconds = 0

        self.create_time = None

        self.next_stop = False
        self.specify_count = False
        self.count = 0
        self.current_task_index = 0
        self.sub_tasks: [PlotSubTask] = []

        self.signalMakingPlot.connect(self.makingPlot)

    def __getstate__(self):
        state = self.__dict__.copy()
        return state

    def __setstate__(self, state):
        super(PlotTask, self).__init__()
        self.__dict__.update(state)

    def start(self):
        self.sub_tasks[0].worker.start()

    def makingPlot(self, task, sub_task):
        if self.next_stop:
            return

        if self.specify_count:
            if self.current_task_index + 1 >= self.count:
                return
            else:
                self.current_task_index += 1
                self.current_sub_task.worker.start()
        else:
            new_sub_task = PlotSubTask(self, self.count)
            self.sub_tasks.append(new_sub_task)

            self.count += 1
            self.current_task_index += 1

            new_sub_task.worker.start()

    def increase(self):
        self.sub_tasks.append(PlotSubTask(self, self.count))
        self.count += 1
        return self.sub_tasks[-1]

    def reduce(self):
        if self.pending_count() == 0:
            return
        self.sub_tasks.remove(self.sub_tasks[-1])
        self.count -= 1

    def pending_count(self):
        count = self.count - (self.current_task_index + 1)
        if count < 0:
            count = 0
        return count

    @property
    def memory_used(self):
        return self.sub_tasks[self.current_task_index].memory_used

    @property
    def working(self):
        for sub in self.sub_tasks:
            if sub.working:
                return True
        return False

    @property
    def status(self):
        return self.sub_tasks[self.current_task_index].status

    @property
    def finish(self):
        for sub in self.sub_tasks:
            if not sub.finish:
                return False
        return True

    @property
    def success(self):
        for sub in self.sub_tasks:
            if not sub.success:
                return False
        return True

    @property
    def suspend(self):
        for sub in self.sub_tasks:
            if sub.suspend:
                return True
        return False

    @property
    def abnormal(self):
        for sub in self.sub_tasks:
            if sub.abnormal:
                return True
        return False

    @property
    def begin_time(self):
        if not self.specify_count:
            return self.current_sub_task.begin_time
        return self.sub_tasks[0].begin_time

    @property
    def end_time(self):
        return self.sub_tasks[-1].end_time

    @property
    def suspended_seconds(self):
        return self.current_sub_task.suspended_seconds

    @property
    def ram(self):
        return self.current_sub_task.ram

    @property
    def progress(self):
        if not self.specify_count:
            return self.current_sub_task.progress

        total_progress = 0
        for sub in self.sub_tasks:
            total_progress += sub.progress
        return total_progress / self.count

    @property
    def current_sub_task(self):
        return self.sub_tasks[self.current_task_index]

    def delay_remain(self):
        if self.delay_seconds == 0:
            return 0
        remain = self.create_time.timestamp() + self.delay_seconds - time.time()
        if remain < 0:
            return 0
        return int(remain)

    def get_temp_files(self):
        all_files = []
        total_size = 0
        try:
            for file in os.listdir(self.temporary_folder):
                full = os.path.join(self.temporary_folder, file)
                if not os.path.isfile(full):
                    continue
                total_size += os.path.getsize(full)
                all_files.append(full)
        except:
            pass
        return all_files, total_size

    def delete_temp_files(self):
        all_files, total_size = self.get_temp_files()
        try:
            for file in all_files:
                os.remove(file)
        except:
            return False
        return True

    def remove_temp_folder(self):
        try:
            shutil.rmtree(self.temporary_folder)
        except:
            return False
        return True


class PlotSubTask(QObject):
    def __init__(self, task: PlotTask, index):
        super(PlotSubTask, self).__init__()

        self.index = index
        self.status = '等待'
        self.finish = False
        self.success = False
        self.abnormal = False
        self.suspend = False
        self.suspend_time = 0
        self.suspend_remain_time = 0

        self.suspended_seconds = 0

        self.begin_time = None
        self.end_time = None
        self.progress = 0.0
        self.ram = 0

        self.plot_file = ''
        self.hdd_folder = task.hdd_folder

        self.log = []

        self.task: PlotTask = task
        self.worker: PlotWorker = PlotWorker(task,  self)

    def __getstate__(self):
        state = self.__dict__.copy()
        if 'worker' in state:
            del state['worker']
        if 'task' in state:
            del state['task']
        return state

    def __setstate__(self, state):
        super(PlotSubTask, self).__init__()
        state['worker'] = None
        state['task'] = None
        self.__dict__.update(state)

    @property
    def working(self):
        if self.worker is None:
            return False
        return self.worker.process is not None

    @property
    def memory_used(self):
        if self.worker is None:
            return 0
        return self.worker.memory_used


class PlotWorker(QThread):
    signalTaskOutput = pyqtSignal(object, object, str)

    def __init__(self, task: PlotTask, sub_task: PlotSubTask):
        super(PlotWorker, self).__init__()

        self.task: PlotTask = task
        self.sub_task: PlotSubTask = sub_task

        self.process = None

        self.plot_filename = ''
        self.copying = False

        self.stopping = False

        self.phase = 0
        self.table = ''
        self.bucket = 0
        self.phase3_first_computation = True

    def get_pos_process(self):
        if self.process is None:
            return None
        try:
            p = psutil.Process(pid=self.process.pid)
            if core.is_debug():
                return p

            ps = p.children()
            for child in ps:
                if child.name().lower() == 'proofofspace.exe':
                    return child
            return None
        except Exception as e:
            return None

    def handleProgress(self, text):
        if text.startswith('Starting phase 1/4'):
            self.phase = 1
            self.task.phase = 1
        elif text.startswith('Computing table'):
            self.table = text
        elif text.startswith('Starting phase 2/4'):
            self.phase = 2
            self.task.phase = 2
        elif text.startswith('Backpropagating on table'):
            self.table = text
        elif text.startswith('Starting phase 3/4'):
            self.phase = 3
            self.task.phase = 3
        elif text.startswith('Compressing tables'):
            self.phase3_first_computation = True
            self.table = text
        elif text.startswith('First computation'):
            self.phase3_first_computation = False
        elif text.startswith('Starting phase 4/4'):
            self.phase = 4
            self.task.phase = 4
        elif text.startswith('Wrote left entries'):
            if self.table == 'Backpropagating on table 7':
                self.sub_task.progress = 29.167
                self.updateTask()
        elif text.startswith('Bucket'):
            r = re.compile(r'Bucket (\d*) ')
            found = re.findall(r, text)
            if not found:
                return
            self.bucket = int(found[0])

            if self.phase == 1:
                if self.table == 'Computing table 2':
                    base_progress = 0.0
                    max_progress = 4.167
                    total_bucket = 127
                elif self.table == 'Computing table 3':
                    base_progress = 4.167
                    max_progress = 8.333
                    total_bucket = 127
                elif self.table == 'Computing table 4':
                    base_progress = 8.333
                    max_progress = 12.500
                    total_bucket = 127
                elif self.table == 'Computing table 5':
                    base_progress = 12.500
                    max_progress = 16.667
                    total_bucket = 127
                elif self.table == 'Computing table 6':
                    base_progress = 16.667
                    max_progress = 20.833
                    total_bucket = 127
                elif self.table == 'Computing table 7':
                    base_progress = 20.833
                    max_progress = 25.000
                    total_bucket = 127
                else:
                    return
            elif self.phase == 2:
                if self.table == 'Backpropagating on table 6':
                    base_progress = 29.167
                    max_progress = 33.333
                    total_bucket = 110
                elif self.table == 'Backpropagating on table 5':
                    base_progress = 33.333
                    max_progress = 37.500
                    total_bucket = 110
                elif self.table == 'Backpropagating on table 4':
                    base_progress = 37.500
                    max_progress = 41.667
                    total_bucket = 110
                elif self.table == 'Backpropagating on table 3':
                    base_progress = 41.667
                    max_progress = 45.833
                    total_bucket = 110
                elif self.table == 'Backpropagating on table 2':
                    base_progress = 45.833
                    max_progress = 50.000
                    total_bucket = 110
                else:
                    return
            elif self.phase == 3:
                if self.table == 'Compressing tables 1 and 2':
                    base_progress = 50.000
                    max_progress = 54.167
                    total_bucket = 127
                elif self.table == 'Compressing tables 2 and 3':
                    base_progress = 54.167
                    max_progress = 58.333
                    total_bucket = 102 + 81 + 1
                    if not self.phase3_first_computation:
                        self.bucket = 102 + 1 + self.bucket
                elif self.table == 'Compressing tables 3 and 4':
                    base_progress = 58.333
                    max_progress = 62.500
                    total_bucket = 102 + 82 + 1
                    if not self.phase3_first_computation:
                        self.bucket = 102 + 1 + self.bucket
                elif self.table == 'Compressing tables 4 and 5':
                    base_progress = 62.500
                    max_progress = 66.667
                    total_bucket = 103 + 83 + 1
                    if not self.phase3_first_computation:
                        self.bucket = 103 + 1 + self.bucket
                elif self.table == 'Compressing tables 5 and 6':
                    base_progress = 66.667
                    max_progress = 70.833
                    total_bucket = 105 + 86 + 1
                    if not self.phase3_first_computation:
                        self.bucket = 105 + 1 + self.bucket
                elif self.table == 'Compressing tables 6 and 7':
                    base_progress = 70.833
                    max_progress = 75.000
                    total_bucket = 110 + 95 + 1
                    if not self.phase3_first_computation:
                        self.bucket = 110 + 1 + self.bucket
                else:
                    return
            elif self.phase == 4:
                base_progress = 75.000
                max_progress = 99.000
                total_bucket = 127
            else:
                return
            # bucket_progress = 100 * self.bucket / total_bucket
            # progress = bucket_progress * max_progress / 100
            self.sub_task.progress = (100*self.bucket/total_bucket) * (max_progress-base_progress) / 100 + base_progress
            self.updateTask()
        elif text.startswith('Final File size'):
            self.copying = True
            self.sub_task.status = '生成文件'
            self.task.signalMakingPlot.emit(self.task, self.sub_task)
            self.updateTask()

            if core.is_debug():
                time.sleep(10)
        elif text.startswith('Copied final file'):
            self.sub_task.progress = 100.0
            self.updateTask()

    def handleLog(self, text):
        text = text.strip()

        failed = False
        finished = False

        self.sub_task.abnormal = False

        if text.startswith('Generating plot for'):
            r = re.compile(r'filename=(.*) id=')
            found = re.findall(r, text)
            if found:
                self.plot_filename = found[0]
        elif text.startswith('Bucket'):
            r = re.compile(r'Ram: (.*)GiB, u_sort')
            found = re.findall(r, text)
            if found:
                ram = float(found[0]) * 2**30
                if self.sub_task.ram != ram:
                    self.sub_task.ram = ram
                    self.updateTask()
        elif text.startswith('time=') and text.count('level='):
            r = re.compile(r'level=(.*) msg=')
            found = re.findall(r, text)
            if found:
                level = found[0]
                if level == 'fatal':
                    failed = True
        elif text.count('Error') and text.count('Retrying'):
            self.sub_task.abnormal = True
        elif text.startswith('Renamed final file from'):
            finished = True

        self.handleProgress(text)

        return failed, finished

    @property
    def memory_used(self):
        try:
            pos_process = self.get_pos_process()
            if pos_process:
                m = pos_process.memory_info()
                return m.private
        except Exception as e:
            pass
        return 0

    def stop(self):
        if self.task.delay_remain():
            self.stopping = True
            return

        self.stopping = True

        try:
            if self.process:
                pos_process = self.get_pos_process()
                self.process.terminate()
                if pos_process:
                    pos_process.resume()
                    pos_process.terminate()
        except:
            pass

    def suspend(self, for_time=0):
        self.sub_task.suspend = True
        self.sub_task.suspend_time = for_time
        self.sub_task.suspend_remain_time = for_time
        self.updateTask()

        if self.process is None:
            return

        try:
            if is_debug():
                p = psutil.Process(pid=self.process.pid)
                p.suspend()
                return
            pos_process = self.get_pos_process()
            if pos_process:
                pos_process.suspend()
        except:
            pass

    def resume(self):
        self.sub_task.suspend = False
        self.sub_task.suspend_time = 0
        self.sub_task.suspend_remain_time = 0
        self.updateTask()

        if self.process is None:
            return

        try:
            if is_debug():
                p = psutil.Process(pid=self.process.pid)
                p.resume()
                return
            pos_process = self.get_pos_process()
            if pos_process:
                pos_process.resume()
        except:
            pass

    def run(self):
        t = self.task

        plat = platform.system()
        if plat == 'Windows':
            folder = 'windows'
            bin_file = 'chia-plotter-windows-amd64.exe'
        elif plat == 'Darwin':
            folder = 'macos'
            bin_file = 'chia-plotter-darwin-amd64'
        elif plat == 'Linux':
            folder = 'linux'
            bin_file = 'chia-plotter-linux-amd64'
        else:
            return False

        if plat == 'Windows' and core.is_debug():
            bin_file = 'test.exe'

        exe_cwd = os.path.join(BASE_DIR, 'bin', folder, 'plotter')
        exe = os.path.join(exe_cwd, bin_file)

        args = [
            exe,
            '-action', 'plotting',
            '-plotting-fpk', t.fpk,
            '-plotting-ppk', t.ppk,
            '-plotting-n', '1',
            '-r', f'{t.number_of_thread}',
            '-b', f'{t.memory_size}',
            '-d', t.hdd_folder,
            '-t', t.temporary_folder,
            '-2', t.temporary_folder,
        ]

        while True:
            delay_remain = self.task.delay_remain()

            if self.stopping:
                self.stopping = False
                self.sub_task.status = '已取消'
                self.sub_task.finish = True
                self.sub_task.success = False
                self.sub_task.end_time = datetime.now()

                for i in range(self.task.current_task_index + 1, self.task.count):
                    rest_sub_task = self.task.sub_tasks[i]
                    rest_sub_task.success = False
                    rest_sub_task.status = '已手动停止'
                    rest_sub_task.finish = True
                    self.updateTask(sub_task=rest_sub_task)
                else:
                    self.updateTask()
                break

            if delay_remain:
                time.sleep(1)
                continue

            self.task.running = False
            if not PlotTaskManager.assign_task(self.task):
                self.sub_task.status = '排队中'
                time.sleep(1)
                continue

            self.sub_task.begin_time = datetime.now()
            self.sub_task.status = '正在执行'
            self.sub_task.progress = 0
            self.updateTask()

            self.process = Popen(args, stdout=PIPE, stderr=PIPE, cwd=exe_cwd, creationflags=CREATE_NO_WINDOW)

            success = True
            finished = False
            while True:
                line = self.process.stdout.readline()

                text = line.decode('utf-8', errors='replace')
                text = text.rstrip()

                if not text and self.process.poll() is not None:
                    break

                if text:
                    self.sub_task.log.append(text)
                    _failed, _finished = self.handleLog(text)
                    if _failed:
                        success = False
                    if _finished:
                        finished = True
                    self.signalTaskOutput.emit(self.task, self.sub_task, text)
                    self.updateTask()

            self.process = None
            self.task.running = False

            stop = False
            failed = False

            plot_path = os.path.join(self.sub_task.hdd_folder, self.plot_filename)

            if self.stopping:
                self.stopping = False
                stop = failed = True
                self.sub_task.status = '已手动停止'
            elif not self.plot_filename:
                stop = failed = True
                self.sub_task.status = '没有plot文件名'
            elif not success or not finished:
                stop = failed = True
                self.sub_task.status = '失败'
            elif not os.path.exists(plot_path) and not is_debug():
                stop = failed = True
                self.sub_task.status = 'plot文件不存在'
            else:
                self.sub_task.status = '完成'
                self.sub_task.finish = True
                self.sub_task.success = True
                self.sub_task.progress = 100.0
                self.sub_task.suspended_seconds = 0
                self.sub_task.end_time = datetime.now()
                self.sub_task.plot_file = plot_path

                self.task.signalNewPlot.emit(self.task, self.sub_task)

                self.updateTask()
                break

            self.updateTask()

            if failed:
                self.sub_task.success = False
                self.sub_task.finish = True
                self.sub_task.end_time = datetime.now()

                break

            if stop:
                for i in range(self.task.current_task_index + 1, self.task.count):
                    rest_sub_task = self.task.sub_tasks[i]
                    rest_sub_task.success = False
                    rest_sub_task.status = '已手动停止'
                    rest_sub_task.finish = True
                    self.updateTask(sub_task=rest_sub_task)
                else:
                    self.updateTask()

                break

    def updateTask(self, task=None, sub_task=None):
        if task is None:
            task = self.task
        if sub_task is None:
            sub_task = self.sub_task

        self.task.signalUpdateTask.emit(task, sub_task)


class PlotTaskManager(QObject):
    signalUpdateTask = pyqtSignal(object, object)
    signalMakingPlot = pyqtSignal(object, object)
    signalNewPlot = pyqtSignal(object, object)

    tasks = []
    task_lock = threading.Lock()

    def __init__(self):
        super(PlotTaskManager, self).__init__()
        self.load_tasks()

    @property
    def working(self):
        for task in PlotTaskManager.tasks:
            if task.working:
                return True
        return False

    def add_task(self, task: PlotTask):
        task.signalUpdateTask.connect(self.signalUpdateTask)
        task.signalMakingPlot.connect(self.signalMakingPlot)
        task.signalNewPlot.connect(self.signalNewPlot)

        PlotTaskManager.tasks.append(task)
        self.save_tasks()

    def remove_task(self, task: PlotTask):
        PlotTaskManager.tasks.remove(task)
        self.save_tasks()

    def load_tasks(self):
        filename = os.path.join(BASE_DIR, 'tasks.pkl')
        if os.path.exists(filename):
            task_data = open(filename, 'rb').read()
            PlotTaskManager.tasks = pickle.loads(task_data)

        changed = False
        for task in PlotTaskManager.tasks:
            for sub_task in task.sub_tasks:
                if not sub_task.finish:
                    sub_task.status = '异常结束'
                    sub_task.end_time = datetime.now()
                    sub_task.finish = True
                changed = True

        if changed:
            self.save_tasks()

    def save_tasks(self):
        filename = os.path.join(BASE_DIR, 'tasks.pkl')
        tasks_data = pickle.dumps(PlotTaskManager.tasks)
        open(filename, 'wb').write(tasks_data)
        return

    @staticmethod
    def assign_task(task: PlotTask):
        PlotTaskManager.task_lock.acquire()

        config = get_config()

        total_count = 0
        phase1_count = 0

        for _task in PlotTaskManager.tasks:
            if _task == task:
                continue
            if _task.working:
                total_count += 1
                if _task.phase == 1:
                    phase1_count += 1

        total_limit = 'total_limit' in config and config['total_limit']
        total_limit_count = 'total_limit_count' in config and config['total_limit_count']
        phase1_limit = 'phase1_limit' in config and config['phase1_limit']
        phase1_limit_count = 'phase1_limit_count' in config and config['phase1_limit_count']

        if total_limit and total_count >= total_limit_count:
            PlotTaskManager.task_lock.release()
            return False

        if phase1_limit and phase1_count >= phase1_limit_count:
            PlotTaskManager.task_lock.release()
            return False

        task.running = True
        PlotTaskManager.task_lock.release()
        return True
