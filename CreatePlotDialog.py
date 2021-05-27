from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtCore import Qt
from ui.CreatePlotDialog import Ui_CreatePlotDialog
from core.plot import PlotTask, PlotSubTask
from config import get_config, save_config
import os
from utils import make_name, size_to_str, get_k_size
from datetime import datetime
from core.disk import get_disk_usage
from PyQt5.QtWidgets import QFileDialog
from core import BASE_DIR, is_debug
import platform
import re
from subprocess import Popen, PIPE, CREATE_NO_WINDOW


class CreatePlotDialog(QDialog, Ui_CreatePlotDialog):
    last_ssd_folder = ''
    last_hdd_folder = ''

    def __init__(self, task: PlotTask=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        config = get_config()

        self.buttonBox.button(self.buttonBox.Ok).setText('创建')
        self.buttonBox.button(self.buttonBox.Cancel).setText('取消')
        self.checkBoxSpecifyCount.stateChanged.connect(self.checkSpecifyCount)
        self.commandLinkButton.clicked.connect(self.aboutPublicKey)

        self.comboK.addItem('101.4GiB (k=32, 临时文件: 239GiB)', 32)
        self.comboK.addItem('208.8GiB (k=33, 临时文件: 521GiB)', 33)
        self.comboK.addItem('429.8GiB (k=34, 临时文件: 1041GiB)', 34)
        self.comboK.addItem('884.1GiB (k=35, 临时文件: 2175GiB)', 35)
        self.comboK.setCurrentIndex(0)

        self.comboCmdLine.addItem('使用内置ProofOfSpace.exe', self.get_builtin_exe())
        chia_exe = self.get_official_chia_exe()
        if chia_exe:
            self.comboCmdLine.addItem('使用钱包chia.exe', chia_exe)
        self.comboCmdLine.addItem('手动选择', 'select')
        self.comboCmdLine.currentIndexChanged.connect(self.changeCmdLine)
        self.comboCmdLine.setCurrentIndex(0)
        self.changeCmdLine()

        def select_cmdline(cmdline):
            for i in range(self.comboCmdLine.count()):
                d = self.comboCmdLine.itemData(i, Qt.UserRole)
                if d == cmdline:
                    self.comboCmdLine.setCurrentIndex(i)
                    return

            self.comboCmdLine.addItem(os.path.basename(cmdline), cmdline)
            self.comboCmdLine.setCurrentIndex(self.comboCmdLine.count()-1)
            self.lineEditCmdLine.setText(cmdline)

        def select_k_combo(k):
            for i in range(self.comboK.count()):
                d = self.comboK.itemData(i, Qt.UserRole)
                if d == k:
                    self.comboK.setCurrentIndex(i)
                    return

        self.modify = False

        if task:
            self.task = task
            self.modify = True

            self.comboSSD.addItem(task.ssd_folder, task.ssd_folder)
            self.comboSSD.setDisabled(True)

            current_index = 0
            self.comboHDD.addItem('自动', 'auto')
            for hdd_folder_obj in config['hdd_folders']:
                folder = hdd_folder_obj['folder']
                text = folder
                if os.path.exists(folder):
                    usage = get_disk_usage(folder)
                    text += f" ({size_to_str(usage.free)}空闲)"
                else:
                    text += " (不存在)"
                if folder == task.hdd_folder:
                    current_index = self.comboHDD.count()
                self.comboHDD.addItem(text, folder)
            if self.task.auto_hdd_folder:
                self.comboHDD.setCurrentIndex(0)
            else:
                self.comboHDD.setCurrentIndex(current_index)

            self.editFpk.setPlainText(task.fpk)
            self.editFpk.setDisabled(True)
            self.editPpk.setPlainText(task.ppk)
            self.editPpk.setDisabled(True)

            self.checkBoxSpecifyCount.setChecked(task.specify_count)
            self.checkBoxSpecifyCount.setDisabled(True)
            self.spinNumber.setValue(task.count)
            self.spinNumber.setDisabled(True)

            self.spinThreadNum.setValue(task.number_of_thread)
            self.spinMemory.setValue(task.memory_size)

            self.timeEditDelay.setDisabled(True)

            self.spinBucketNum.setValue(task.buckets)
            select_k_combo(task.k)
            self.checkBoxBitfield.setChecked(task.bitfield)
            select_cmdline(task.cmdline)

            self.setWindowTitle('编辑P图任务')

            self.buttonBox.button(self.buttonBox.Ok).setText('修改')
        else:
            self.task = PlotTask()

            current_index = 0
            for ssd_folder in config['ssd_folders']:
                text = ssd_folder
                if os.path.exists(ssd_folder):
                    usage = get_disk_usage(ssd_folder)
                    text += f" ({size_to_str(usage.free)}空闲)"
                else:
                    text += " (不存在)"
                if ssd_folder == CreatePlotDialog.last_ssd_folder:
                    current_index = self.comboSSD.count()
                self.comboSSD.addItem(text, ssd_folder)
            self.comboSSD.setCurrentIndex(current_index)

            current_index = 0
            self.comboHDD.addItem('自动', 'auto')
            for hdd_folder_obj in config['hdd_folders']:
                folder = hdd_folder_obj['folder']
                text = folder
                if os.path.exists(folder):
                    usage = get_disk_usage(folder)
                    text += f" ({size_to_str(usage.free)}空闲)"
                else:
                    text += " (不存在)"
                if folder == CreatePlotDialog.last_hdd_folder:
                    current_index = self.comboHDD.count()
                self.comboHDD.addItem(text, folder)
            self.comboHDD.setCurrentIndex(current_index)

            fpk = ''
            ppk = ''
            if 'fpk' in config:
                fpk = config['fpk']

            if 'ppk' in config:
                ppk = config['ppk']

            if not fpk and not ppk and chia_exe:
                fpk, ppk = self.get_fpk_ppk(chia_exe)

            self.editFpk.setPlainText(fpk)
            self.editPpk.setPlainText(ppk)

            if 'num' in config:
                self.spinNumber.setValue(config['num'])

            if 'thread_num' in config:
                self.spinThreadNum.setValue(config['thread_num'])

            if 'memory_size' in config:
                self.spinMemory.setValue(config['memory_size'])

            if 'specify_count' in config:
                self.checkBoxSpecifyCount.setChecked(config['specify_count'])
                if config['specify_count']:
                    self.spinNumber.setDisabled(False)

            if 'buckets' in config:
                self.spinBucketNum.setValue(config['buckets'])

            if 'k' in config:
                select_k_combo(config['k'])

            self.checkBoxBitfield.setChecked(True)
            if 'bitfield' in config:
                self.checkBoxBitfield.setChecked(config['bitfield'])

            if 'cmdline' in config:
                select_cmdline(config['cmdline'])

        self.checkBoxBitfield.stateChanged.connect(self.checkBitfield)

    def get_builtin_exe(self):
        plat = platform.system()
        if plat == 'Windows':
            folder = 'windows'
        elif plat == 'Darwin':
            folder = 'macos'
        elif plat == 'Linux':
            folder = 'linux'
        else:
            return ''
        exe_cwd = os.path.join(BASE_DIR, 'bin', folder, 'plotter')
        if is_debug():
            return os.path.join(exe_cwd, 'test.exe')
        return os.path.join(exe_cwd, 'ProofOfSpace.exe')

    def changeCmdLine(self):
        data = self.comboCmdLine.currentData(Qt.UserRole)
        if data == 'select':
            chia_exe = QFileDialog.getOpenFileName(self, '选择钱包chia.exe', directory=os.getenv('LOCALAPPDATA'), filter='chia.exe')[0]
            self.lineEditCmdLine.setText(chia_exe)
        else:
            self.lineEditCmdLine.setText(data)

    @staticmethod
    def get_fpk_ppk(chia_exe):
        args = [
            chia_exe,
            'keys',
            'show',
        ]
        process = Popen(args, stdout=PIPE, stderr=PIPE, cwd=os.path.dirname(chia_exe), creationflags=CREATE_NO_WINDOW)

        fpk = ''
        ppk = ''

        while True:
            line = process.stdout.readline()

            text = line.decode('utf-8', errors='replace')
            if not text and process.poll() is not None:
                break

            text = text.rstrip()

            if text.startswith('Farmer public key'):
                r = re.compile(r': (.*)')
                found = re.findall(r, text)
                if found:
                    fpk = found[0]
            elif text.startswith('Pool public key'):
                r = re.compile(r': (.*)')
                found = re.findall(r, text)
                if found:
                    ppk = found[0]

        return fpk, ppk

    @staticmethod
    def get_official_chia_exe():
        app_data = os.getenv('LOCALAPPDATA')
        if app_data is None:
            return ''
        folder = os.path.join(app_data, 'chia-blockchain')
        if not os.path.exists(folder):
            return ''

        app_folder = ''
        for o in os.listdir(folder):
            if not o.startswith('app-'):
                continue
            sub_folder = os.path.join(folder, o)
            if os.path.isdir(sub_folder):
                app_folder = sub_folder

        if not app_folder:
            return ''

        chia_exe = os.path.join(app_folder, 'resources', 'app.asar.unpacked', 'daemon', 'chia.exe')
        if not os.path.exists(chia_exe):
            return ''
        return chia_exe

    def aboutPublicKey(self):
        QMessageBox.information(self, '提示', '该软件不会向用户索要助记词。\n如果你已经安装了Chia官方钱包软件并且创建了钱包，fpk和ppk会自动获取。如果没有安装，请使用第三方工具（如：HPool提供的签名软件等）来生成。')

    def checkBitfield(self, value):
        if value == 0:
            if QMessageBox.information(self, '提示', f'禁止位域会导致P图过程效率低且临时文件大，确定要禁止吗？',
                                       QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                self.checkBoxBitfield.setCheckState(2)

    def checkSpecifyCount(self):
        self.spinNumber.setDisabled(not self.checkBoxSpecifyCount.isChecked())

    def accept(self) -> None:
        if self.modify:
            thread_num = self.spinThreadNum.value()
            memory_size = self.spinMemory.value()
            buckets = self.spinBucketNum.value()
            k = int(self.comboK.currentData(Qt.UserRole))
            bitfield = self.checkBoxBitfield.isChecked()
            hdd_folder = self.comboHDD.currentData(Qt.UserRole)
            cmdline = self.lineEditCmdLine.text()

            if not cmdline:
                QMessageBox.information(self, '提示', '请选择程序')
                return

            if hdd_folder == 'auto':
                self.task.auto_hdd_folder = True
            else:
                self.task.auto_hdd_folder = False
                self.task.hdd_folder = hdd_folder

            self.task.number_of_thread = thread_num
            self.task.memory_size = memory_size
            self.task.buckets = buckets
            self.task.k = k
            self.task.bitfield = bitfield
            self.task.cmdline = cmdline
            self.task.inner_cmdline = cmdline == self.get_builtin_exe()
            self.task.official_cmdline = cmdline == self.get_official_chia_exe()
            super().accept()
            return
        fpk = self.editFpk.toPlainText()
        ppk = self.editPpk.toPlainText()
        buckets = self.spinBucketNum.value()
        k = int(self.comboK.currentData(Qt.UserRole))
        bitfield = self.checkBoxBitfield.isChecked()
        cmdline = self.lineEditCmdLine.text()

        ssd_folder = self.comboSSD.currentData()
        hdd_folder = self.comboHDD.currentData()

        CreatePlotDialog.last_ssd_folder = ssd_folder
        CreatePlotDialog.last_hdd_folder = hdd_folder

        delayTime = self.timeEditDelay.time()
        delay = delayTime.hour() * 60*60 + delayTime.minute() * 60 + delayTime.second()

        specify_count = self.checkBoxSpecifyCount.isChecked()
        number = self.spinNumber.value()
        thread_num = self.spinThreadNum.value()
        memory_size = self.spinMemory.value()

        if not cmdline:
            QMessageBox.information(self, '提示', '请选择程序')
            return

        if not os.path.exists(ssd_folder):
            QMessageBox.information(self, '提示', '临时目录不存在')
            return

        if hdd_folder != 'auto' and not os.path.exists(hdd_folder):
            QMessageBox.information(self, '提示', '最终目录不存在')
            return

        if not fpk:
            QMessageBox.information(self, '提示', '请输入fpk')
            return

        if not ppk:
            QMessageBox.information(self, '提示', '请输入ppk')
            return

        if fpk.startswith('0x'):
            fpk = fpk[2:]
        if ppk.startswith('0x'):
            ppk = ppk[2:]

        if len(fpk) != 96:
            QMessageBox.information(self, '提示', 'fpk格式错误，请检查')
            return
        if len(ppk) != 96:
            QMessageBox.information(self, '提示', 'ppk格式错误，请检查')
            return

        if not specify_count:
            number = 1

        config = get_config()

        config['cmdline'] = cmdline
        config['fpk'] = fpk
        config['ppk'] = ppk
        config['buckets'] = buckets
        config['k'] = k
        config['bitfield'] = bitfield
        config['specify_count'] = specify_count
        config['num'] = number
        config['thread_num'] = thread_num
        config['memory_size'] = memory_size

        save_config()

        temporary_folder = os.path.join(ssd_folder, make_name(12))
        temporary_folder = temporary_folder.replace('\\', '/')

        try:
            os.mkdir(temporary_folder)
        except:
            QMessageBox.information(self, '提示', '创建临时目录失败 %s' % temporary_folder)
            return

        if hdd_folder != 'auto':
            hdd_usage = get_disk_usage(hdd_folder)

            if hdd_usage is None:
                QMessageBox.information(self, '提示', f'目录{hdd_folder}无法使用')
                return

            k_size = get_k_size(k)
            if not is_debug() and hdd_usage.free < k_size:
                if QMessageBox.information(self, '提示', f'最终目录的空间不足{size_to_str(k_size)}，确定要继续吗？', QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                    return

        self.task.cmdline = cmdline
        self.task.inner_cmdline = cmdline == self.get_builtin_exe()
        self.task.official_cmdline = cmdline == self.get_official_chia_exe()
        self.task.create_time = datetime.now()
        self.task.fpk = fpk
        self.task.ppk = ppk
        self.task.buckets = buckets
        self.task.k = k
        self.task.bitfield = bitfield
        self.task.ssd_folder = ssd_folder
        if hdd_folder == 'auto':
            self.task.auto_hdd_folder = True
        else:
            self.task.auto_hdd_folder = False
            self.task.hdd_folder = hdd_folder
        self.task.temporary_folder = temporary_folder
        self.task.specify_count = specify_count
        self.task.count = number
        self.task.number_of_thread = thread_num
        self.task.memory_size = memory_size
        self.task.delay_seconds = delay

        if specify_count:
            for i in range(number):
                self.task.sub_tasks.append(PlotSubTask(self.task, i))
        else:
            self.task.sub_tasks.append(PlotSubTask(self.task, 0))

        super().accept()
