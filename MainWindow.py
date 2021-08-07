import sys
import os
import cgitb
import tempfile
import traceback
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from PyQt5.Qt import pyqtSignal
from ui.MainWindow import Ui_MainWindow
from core.plot import PlotTaskManager
from version import version, beta
from core.disk import disk_operation
from core.wallet import wallet_manager
from core import BASE_DIR
from config import save_config, get_config
from subprocess import run
from utils import is_auto_launch, setup_auto_launch


class MainWindow(QMainWindow, Ui_MainWindow):
    signalException = pyqtSignal(str, object, object, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.setup_exception_handle()

        disk_operation.start()
        wallet_manager.start()

        self.tabFoldersWidget.setMainWindow(self)
        self.tabPlotWidget.setMainWindow(self)
        self.tabHPoolOGMineWidget.setMainWindow(self)
        self.tabHPoolPPMineWidget.setMainWindow(self)
        self.tabHuobiPoolMineWidget.setMainWindow(self)

        config = get_config()
        if 'current_tab_index' in config:
            current_tab_index = config['current_tab_index']
            self.tabWidget.setCurrentIndex(current_tab_index)

        self.tabWidget.currentChanged.connect(self.tabChanged)

        self.setWindowTitle('ChiaTools - ' + version + (' - ' + beta if beta else ''))

    def setup_exception_handle(self):
        logs_dir = os.path.join(BASE_DIR, 'logs')
        if not os.path.exists(logs_dir):
            os.mkdir(logs_dir)

        self.signalException.connect(self.on_exception)

        sys.excepthook = self.exception_handler

    def exception_handler(self, etype, evalue, etb):
        logdir = os.path.join(BASE_DIR, 'logs')

        try:
            text = cgitb.text((etype, evalue, etb))
        except:
            text = ''.join(traceback.format_exception(etype, evalue, etb))

        (fd, path) = tempfile.mkstemp(suffix='.log', dir=logdir)

        try:
            with os.fdopen(fd, 'w') as file:
                file.write(text)
        except:
            pass

        self.signalException.emit(path, etype, evalue, etb)

    def on_exception(self, path, etype, evalue, etb):
        msg = ''.join(traceback.format_exception(etype, evalue, etb))

        msg += f'\n请将产生的错误日志文件 {path} 发送给作者以帮助解决该问题。\n\n点击确定后可以继续使用软件。'
        QMessageBox.warning(self, '发生异常', msg)

        run('explorer /select, ' + path)

    def tabChanged(self, index):
        config = get_config()
        config['current_tab_index'] = index

    def restartMine(self, log=''):
        self.tabHPoolOGMineWidget.restartMine(log)
        self.tabHPoolPPMineWidget.restartMine(log)
        self.tabHuobiPoolMineWidget.restartMine(log)

    def setup_auto_launch(self):
        config = get_config()

        hpool_auto_start = 'hpool_auto_mine' in config and config['hpool_auto_mine']
        hpool_pp_auto_mine = 'hpool_pp_auto_mine' in config and config['hpool_pp_auto_mine']
        huobipool_auto_mine = 'huobipool_auto_mine' in config and config['huobipool_auto_mine']

        setup_auto_launch(hpool_auto_start or hpool_pp_auto_mine or huobipool_auto_mine)

    def closeEvent(self, event):
        if self.tabHPoolOGMineWidget.mine_process or \
                self.tabHPoolPPMineWidget.mine_process or \
                self.tabHuobiPoolMineWidget.mine_process:
            QMessageBox.warning(self, '提示', '请先停止挖矿')
            event.ignore()
            return

        if self.tabPlotWidget.task_manager.working:
            QMessageBox.warning(self, '提示', '请先停止Plot任务')
            event.ignore()
            return

        if self.tabPlotCheckWidget.worker:
            QMessageBox.warning(self, '提示', '请先停止Plot检查')
            event.ignore()
            return

        PlotTaskManager.save_tasks()
        save_config()
