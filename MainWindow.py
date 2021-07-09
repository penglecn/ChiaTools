from PyQt5.QtWidgets import QMainWindow, QMessageBox
from ui.MainWindow import Ui_MainWindow
from core.plot import PlotTaskManager
from version import version, beta
from core.disk import disk_operation
from core.wallet import wallet_manager
from config import save_config, get_config


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        disk_operation.start()
        wallet_manager.start()

        self.tabFoldersWidget.setMainWindow(self)
        self.tabPlotWidget.setMainWindow(self)
        self.tabHPoolMineWidget.setMainWindow(self)
        self.tabHuobiPoolMineWidget.setMainWindow(self)

        config = get_config()
        if 'current_tab_index' in config:
            current_tab_index = config['current_tab_index']
            self.tabWidget.setCurrentIndex(current_tab_index)

        self.tabWidget.currentChanged.connect(self.tabChanged)

        self.setWindowTitle('ChiaTools - ' + version + (' - ' + beta if beta else ''))

    def tabChanged(self, index):
        config = get_config()
        config['current_tab_index'] = index

    def closeEvent(self, event):
        if self.tabHPoolMineWidget.mine_process or self.tabHuobiPoolMineWidget.mine_process:
            QMessageBox.warning(self, '提示', '请先停止挖矿')
            event.ignore()
            return

        if self.tabPlotWidget.task_manager.working:
            QMessageBox.warning(self, '提示', '请先停止Plot任务')
            event.ignore()
            return

        PlotTaskManager.save_tasks()
        save_config()
