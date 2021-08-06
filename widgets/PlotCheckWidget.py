from PyQt5.QtWidgets import QWidget, QMessageBox
from ui.PlotCheckWidget import Ui_PlotCheckWidget
from utils import get_official_chia_exe
from core.plot.check import PlotCheckWorker, PlotInfo
from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QHeaderView


class PlotCheckWidget(QWidget, Ui_PlotCheckWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.treePlots.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        # self.treePlots.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.treePlots.customContextMenuRequested.connect(self.showTaskMenu)

        self.plots: dict = {}

        self.worker: Optional[PlotCheckWorker] = None

        self.buttonStart.clicked.connect(self.on_start_check)

    def on_start_check(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
            self.buttonStart.setText('开始检查')
            return

        chia_exe, chia_ver = get_official_chia_exe()

        if not chia_exe:
            QMessageBox.information(self, '提示', '需要先安装Chia官方钱包软件')
            return

        self.treePlots.clear()
        self.plots.clear()

        self.buttonStart.setText('停止检查')
        self.worker = PlotCheckWorker(chia_exe, chia_ver)

        self.worker.signalFoundPlot.connect(self.on_found_plot)
        self.worker.signalCheckingPlot.connect(self.on_checking_plot)
        self.worker.signalCheckResult.connect(self.on_check_result)
        self.worker.signalFinish.connect(self.on_finish)

        self.worker.start()

    def on_found_plot(self, plot_info: PlotInfo):
        if plot_info.path not in self.plots:
            self.plots[plot_info.path] = plot_info
            self.add_item(plot_info)

    def on_checking_plot(self, path, ppk, fpk):
        if path not in self.plots:
            return

        pi = self.plots[path]
        item = self.get_item(pi)
        if not item:
            return

        pi.ppk = ppk
        pi.fpk = fpk
        pi.status = '检查中'

        self.update_item(item, pi)

    def on_check_result(self, path, quality):
        if path not in self.plots:
            return

        pi = self.plots[path]
        item = self.get_item(pi)
        if not item:
            return

        pi.quality = quality
        pi.status = '完成'

        self.update_item(item, pi)

    def on_finish(self):
        self.worker = None
        self.buttonStart.setText('开始检查')

    def add_item(self, plot_info: PlotInfo):
        item = QTreeWidgetItem()
        item.setData(0, Qt.UserRole, plot_info)

        self.treePlots.addTopLevelItem(item)

        self.update_item(item, plot_info)

    def get_item(self, plot_info):
        for i in range(self.treePlots.topLevelItemCount()):
            item = self.treePlots.topLevelItem(i)
            if item.data(0, Qt.UserRole) == plot_info:
                return item
        return None

    def update_item(self, item: QTreeWidgetItem, pi: PlotInfo):
        index = 0
        item.setText(index, pi.filename)

        index += 1
        item.setText(index, pi.k)

        index += 1
        item.setText(index, pi.status)

        index += 1
        item.setText(index, pi.quality)

        index += 1
        item.setText(index, pi.fpk)

        index += 1
        item.setText(index, pi.ppk)
