from PyQt5.Qt import pyqtSignal
from PyQt5.Qt import QThread
from subprocess import Popen, PIPE, STDOUT, CREATE_NO_WINDOW
import os
import re


class PlotInfo(object):
    def __init__(self):
        super().__init__()

        self.filename = ''
        self.path = ''
        self.k = ''
        self.ppk = ''
        self.fpk = ''
        self.status = ''
        self.quality = ''


class PlotCheckWorker(QThread):
    signalFoundPlot = pyqtSignal(PlotInfo)
    signalCheckingPlot = pyqtSignal(str, str, str)
    signalCheckResult = pyqtSignal(str, str)
    signalFinish = pyqtSignal()

    def __init__(self, chia_exe, chia_ver):
        super(PlotCheckWorker, self).__init__()

        self.chia_exe = chia_exe
        self.chia_ver = chia_ver

        self.stopping = False
        self.process = None

        self.checking_plot_path = ''
        self.checking_plot_ppk = ''
        self.checking_plot_fpk = ''

    def stop(self):
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

    @property
    def working(self):
        return self.process is not None

    def handle_output(self, line):
        if 'Found plot' in line:
            r = re.compile(r'Found plot (.*) of size (\d*)')
            found = re.findall(r, line)
            if not found:
                return
            if len(found[0]) != 2:
                return
            path, k = found[0]

            pi = PlotInfo()
            pi.path = path
            pi.filename = os.path.basename(path)
            pi.k = k

            self.signalFoundPlot.emit(pi)
        elif 'Testing plot' in line:
            r = re.compile(r'Testing plot (.*) k=')
            found = re.findall(r, line)
            if not found:
                return
            self.checking_plot_path = found[0]
            self.checking_plot_ppk = ''
            self.checking_plot_fpk = ''
        elif 'Pool public key' in line:
            r = re.compile(r'Pool public key: (.*)')
            found = re.findall(r, line)
            if not found:
                return
            self.checking_plot_ppk = found[0]
            if self.checking_plot_ppk == 'None':
                self.checking_plot_ppk = ''
        elif 'Farmer public key' in line:
            r = re.compile(r'Farmer public key: (.*)')
            found = re.findall(r, line)
            if not found:
                return
            self.checking_plot_fpk = found[0]
            if self.checking_plot_path:
                self.signalCheckingPlot.emit(self.checking_plot_path, self.checking_plot_ppk, self.checking_plot_fpk)
                self.checking_plot_ppk = ''
                self.checking_plot_fpk = ''
        elif 'Proofs' in line and ', ' in line:
            r = re.compile(r'Proofs .*, (.*)')
            found = re.findall(r, line)
            if not found:
                return
            quality = found[0]
            if self.checking_plot_path:
                self.signalCheckResult.emit(self.checking_plot_path, quality)
                self.checking_plot_path = ''

    def remove_escape_code(self, line):
        found = re.findall(re.compile(r'(\x1B\[([0-9]{1,3}(;[0-9]{1,2})?)?[mGK])'), line)
        for f in found:
            line = line.replace(f[0], '')
        return line

    def run(self):
        os.environ['ANSIBLE_FORCE_COLOR'] = "TRUE"

        args = [self.chia_exe, 'plots', 'check']
        self.process = Popen(args, stdout=PIPE, stderr=STDOUT, cwd=os.path.dirname(self.chia_exe),
                             creationflags=CREATE_NO_WINDOW)

        while True:
            line = self.process.stdout.readline()

            if not line and self.process.poll() is not None:
                break

            orig_text = line.decode('utf-8', errors='replace')
            orig_text = self.remove_escape_code(orig_text)

            text = orig_text.rstrip()

            if text:
                self.handle_output(text)

        self.process = None
        self.signalFinish.emit()
