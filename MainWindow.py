from PyQt5.QtWidgets import QMainWindow, QMessageBox
from ui.MainWindow import Ui_MainWindow
from core.plot import PlotTaskManager
from version import version, beta


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self.tabFoldersWidget.setMainWindow(self)
        self.tabPlotWidget.setMainWindow(self)
        self.tabMineWidget.setMainWindow(self)

        self.setWindowTitle('ChiaTools - ' + version + (' - ' + beta if beta else ''))

    def closeEvent(self, event):
        if self.tabMineWidget.mine_process:
            QMessageBox.warning(self, '提示', '请先停止挖矿')
            event.ignore()
            return

        if self.tabPlotWidget.task_manager.working:
            QMessageBox.warning(self, '提示', '请先停止Plot任务')
            event.ignore()
            return

        PlotTaskManager.save_tasks()
