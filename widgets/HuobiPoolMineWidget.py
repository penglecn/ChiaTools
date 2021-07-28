from PyQt5.QtWidgets import QWidget, QMessageBox
from PyQt5.Qt import pyqtSignal, QTimerEvent
from ui.HuobiPoolMineWidget import Ui_HuobiPoolMineWidget
from PyQt5.QtCore import Qt
from config import save_config, get_config
from utils import size_to_str
from datetime import datetime, timedelta
import os
from core import BASE_DIR
from subprocess import Popen, PIPE, STDOUT, CREATE_NO_WINDOW
import socket
import threading
import platform
import time
from core.disk import disk_operation
from utils import is_auto_launch, setup_auto_launch
import psutil


class HuobiPoolMineWidget(QWidget, Ui_HuobiPoolMineWidget):
    signalMineLog = pyqtSignal(str)
    signalMineTerminated = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.main_window = None

        self.mine_process = None
        self.mine_terminating = False
        self.mine_restarting = False

        self.last_mine_log_time = 0

        self.signalMineLog.connect(self.outputMineLog)
        self.signalMineTerminated.connect(self.mineTerminated)

        self.timerIdUpdateSpace = self.startTimer(1000 * 10)

        config = get_config()

        if 'huobipool_miner_name' in config:
            self.editMinerName.setText(config['huobipool_miner_name'])
        else:
            self.editMinerName.setText(socket.gethostname())
            self.saveMineConfig()
        self.editMinerName.editingFinished.connect(self.saveMineConfig)

        if 'huobipool_access_id' in config:
            self.editApiKey.setText(config['huobipool_access_id'])
        self.editApiKey.editingFinished.connect(self.saveMineConfig)

        self.buttonStart.clicked.connect(self.clickStartMine)
        self.checkBoxAutoStart.stateChanged.connect(self.checkAutoStart)

        self.timerIdCheckProcess = self.startTimer(1000)

        disk_operation.signalResult.connect(self.slotDiskOperation)

    def setMainWindow(self, win):
        self.main_window = win

        config = get_config()

        auto_start = False
        if 'huobipool_auto_mine' in config:
            auto_start = config['huobipool_auto_mine']

        if auto_start:
            self.checkBoxAutoStart.setChecked(True)
            self.startMine()

    def timerEvent(self, event: QTimerEvent) -> None:
        timer = event.timerId()

        if timer == self.timerIdUpdateSpace:
            disk_operation.updateMiningPlotTotalInfo()
        elif timer == self.timerIdCheckProcess:
            if not self.mine_process:
                return
            if self.last_mine_log_time == 0:
                return
            if time.time() - self.last_mine_log_time > 60*2:
                self.last_mine_log_time = 0
                self.restartMine('等待超时，重启挖矿进程')

            try:
                p = psutil.Process(pid=self.mine_process.pid)
                m = p.memory_info()
                if m.private > 1024*1024*500:
                    self.restartMine('挖矿进程的内存超过500M，重启挖矿进程')
            except:
                pass

    def slotDiskOperation(self, name, opt):
        result = opt['result']

        if name == 'updateMiningPlotTotalInfo':
            yesterday_count = result['yesterday_count']
            today_count = result['today_count']
            total_count = result['total_count']
            total_size = result['total_size']

            status = f'昨天文件数{yesterday_count}个 今天文件数{today_count}个 总文件数{total_count}个 算力{size_to_str(total_size)}'
            self.labelStatus.setText(status)

    def checkMineLog(self, text):
        if 'The operation completed successfully.' in text:
            return False

        return True

    def outputMineLog(self, text):
        text = text.strip()

        if not text:
            return

        if not self.checkMineLog(text):
            return

        self.last_mine_log_time = time.time()

        self.textEditLog.append(text)

        log_size = len(self.textEditLog.toPlainText())
        if log_size > 1024 * 1024:
            self.textEditLog.clear()

    def minerLog(self, text):
        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.textEditLog.append(dt + ' ' + text)

    def mineTerminated(self):
        self.editMinerName.setDisabled(False)
        self.editApiKey.setDisabled(False)
        self.buttonStart.setText('开始挖矿')

        index = self.main_window.tabWidget.indexOf(self.main_window.tabHuobiPoolMine)
        self.main_window.tabWidget.setTabText(index, '火币矿池挖矿')

        if self.mine_restarting:
            self.mine_restarting = False
            self.startMine()
            return

        if not self.mine_terminating:
            self.minerLog('挖矿意外停止')
            self.minerLog('正在重新挖矿...')

            self.mine_process = None
            self.startMine()
            return

        self.minerLog('挖矿已停止')

        self.mine_terminating = False

    def saveMineConfig(self):
        miner_name = self.editMinerName.text()
        apikey = self.editApiKey.text()

        config = get_config()

        config['huobipool_miner_name'] = miner_name
        config['huobipool_access_id'] = apikey

        save_config()

    def restartMine(self, log=''):
        if self.mine_process is None:
            return

        if not log:
            log = '配置已更改，正在重新挖矿...'
        self.minerLog(log)

        self.mine_restarting = True

        self.mine_process.terminate()

    def checkAutoStart(self, i):
        config = get_config()

        auto_start = self.checkBoxAutoStart.isChecked()
        config['huobipool_auto_mine'] = auto_start
        save_config()

        hpool_auto_start = config['hpool_auto_mine'] if 'hpool_auto_mine' in config else False

        setup_auto_launch(auto_start or hpool_auto_start)

    def clickStartMine(self):
        if not self.mine_process:
            self.textEditLog.clear()

        self.startMine(manual=True)

    def startMine(self, manual=False):
        if self.mine_process:
            self.mine_terminating = True
            self.mine_process.terminate()
            return

        config = get_config()

        if 'hdd_folders' not in config or not config['hdd_folders']:
            QMessageBox.information(self, '提示', '请先配置硬盘')
            return

        miner_name = config['huobipool_miner_name']
        apikey = config['huobipool_access_id']

        if not miner_name:
            self.editMinerName.setFocus()
            return

        if not apikey:
            self.editApiKey.setFocus()
            return

        if len(apikey) != 36:
            QMessageBox.information(self, '提示', 'Access-ID长度是36，请检查')
            return

        if manual and self.main_window.tabHPoolMineWidget.mine_process:
            if QMessageBox.information(self, '警告',
                                       f"确定要双挖吗？\n双挖后一旦爆块，矿池将会对你进行永久性封号！",
                                       QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return

        if not self.generateMineConfig():
            return

        t = threading.Thread(target=self.mineThread)
        t.start()

        self.editMinerName.setDisabled(True)
        self.editApiKey.setDisabled(True)
        self.buttonStart.setText('停止挖矿')

        index = self.main_window.tabWidget.indexOf(self.main_window.tabHuobiPoolMine)
        self.main_window.tabWidget.setTabText(index, '火币矿池挖矿（正在挖矿）')

    def generateMineConfig(self):
        config = get_config()

        if 'hdd_folders' not in config or not config['hdd_folders']:
            QMessageBox.information(self, '提示', '请先配置最终目录')
            return False

        plat = platform.system()
        if plat == 'Windows':
            folder = 'windows'
        else:
            return False

        config_dir = os.path.join(BASE_DIR, 'bin', folder, 'miner', 'huobi', 'config')
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)
        config_file = os.path.join(config_dir, 'config.yaml')

        paths = ''

        for folder_obj in config['hdd_folders']:
            if not folder_obj['mine'] or folder_obj['new_plot']:
                continue
            folder = folder_obj['folder']
            if paths:
                paths += u'\n'
            paths += f'- {folder}'

        if not paths:
            QMessageBox.information(self, '提示', '最终目录中没有可以挖矿的目录')
            return False

        content = f'''access_id: {config['huobipool_access_id']}
worker_name: {config['huobipool_miner_name']}
scan_interval: 3600
plots_dir:
{paths}
'''

        try:
            open(config_file, 'w', encoding='utf-8').write(content)
        except Exception as e:
            return False

        return True

    def mineThread(self):
        plat = platform.system()
        if plat == 'Windows':
            folder = 'windows'
            bin_file = 'HuobiPool-Chia-Miner.exe'
        else:
            self.signalMineLog.emit(f'unknown platform {plat}')
            return False

        exe_file = os.path.join(BASE_DIR, 'bin', folder, 'miner', 'huobi', bin_file)

        self.mine_process = Popen([exe_file], cwd=os.path.dirname(exe_file), stdout=PIPE, stderr=STDOUT, creationflags=CREATE_NO_WINDOW)

        while True:
            if self.mine_process is None:
                break
            line = self.mine_process.stdout.readline()
            text = line.decode('utf-8')
            if not text and self.mine_process.poll() is not None:
                break
            self.signalMineLog.emit(text)

        self.mine_process = None

        self.signalMineTerminated.emit()
