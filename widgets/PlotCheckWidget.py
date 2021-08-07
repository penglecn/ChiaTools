from PyQt5.QtWidgets import QWidget, QMessageBox, QMenu

import core
from ui.PlotCheckWidget import Ui_PlotCheckWidget
from utils import get_official_chia_exe
from core.plot.check import PlotCheckWorker, PlotInfo
from typing import Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem, QHeaderView
from PyQt5.Qt import QCursor
from subprocess import run
import os


class PlotCheckWidget(QWidget, Ui_PlotCheckWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.treePlots.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.treePlots.header().setStretchLastSection(False)
        self.treePlots.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treePlots.customContextMenuRequested.connect(self.on_show_menu)

        self.treePlots.sortByColumn(2, Qt.DescendingOrder)

        self.plots: dict = {}
        self.checked_count = 0
        self.current_checking_plot_info: Optional[PlotInfo] = None

        self.worker: Optional[PlotCheckWorker] = None

        self.buttonStart.clicked.connect(self.on_start_check)

        self.update_total()

    def on_show_menu(self, pos):
        items = self.treePlots.selectedItems()

        if not items:
            return

        plots = []

        for item in items:
            pi = item.data(0, Qt.UserRole)
            plots.append(pi)

        menu = QMenu(self)

        action_locate = None
        action_delete = None

        if len(items) == 1:
            action_locate = menu.addAction(u"浏览文件")
        action_delete = menu.addAction(u"删除")

        action = menu.exec(QCursor.pos())

        if not action:
            return

        if action == action_locate:
            run('explorer /select, ' + plots[0].path)
        elif action == action_delete:
            if QMessageBox.information(self, '提示', f"确定要删除这{len(plots)}个文件吗？\n删除后将无法恢复。",
                                       QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return
            for pi in plots:
                try:
                    os.remove(pi.path)
                except:
                    if not core.is_debug():
                        QMessageBox.information(self, '提示', f"删除文件失败\n{pi.path}\n请检查文件是否被占用。")
                        return
                item = self.get_item(pi)
                self.treePlots.takeTopLevelItem(self.treePlots.indexOfTopLevelItem(item))
                del self.plots[pi.path]

    def on_start_check(self):
        if self.worker:
            self.worker.stop()
            self.worker = None
            self.buttonStart.setText('开始检查')
            self.spinChallengeCount.setEnabled(True)

            if self.current_checking_plot_info:
                item = self.get_item(self.current_checking_plot_info)
                self.current_checking_plot_info.status = ''
                self.update_item(item, self.current_checking_plot_info)
                self.current_checking_plot_info = None
            return

        chia_exe, chia_ver = get_official_chia_exe()

        if not chia_exe:
            QMessageBox.information(self, '提示', '需要先安装Chia官方钱包软件')
            return

        self.treePlots.clear()
        self.plots.clear()
        self.checked_count = 0
        self.update_total()

        self.buttonStart.setText('停止检查')
        self.spinChallengeCount.setEnabled(False)
        self.worker = PlotCheckWorker(chia_exe, chia_ver, self.spinChallengeCount.value())

        self.worker.signalFoundPlot.connect(self.on_found_plot)
        self.worker.signalCheckingPlot.connect(self.on_checking_plot)
        self.worker.signalCheckResult.connect(self.on_check_result)
        self.worker.signalFinish.connect(self.on_finish)

        self.worker.start()

    def update_total(self):
        total_count = len(self.plots)
        percent = 0
        if total_count:
            percent = self.checked_count * 100 / total_count
        status = f'数量{self.checked_count}/{total_count} 进度'
        self.progressCheck.setValue(percent)
        self.labelTotal.setText(status)

    def on_found_plot(self, plot_info: PlotInfo):
        if plot_info.path not in self.plots:
            self.plots[plot_info.path] = plot_info
            self.add_item(plot_info)
            self.update_total()

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

        self.current_checking_plot_info = pi

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

        self.current_checking_plot_info = None

        self.update_item(item, pi)

        self.checked_count += 1
        self.update_total()

    def on_finish(self):
        self.worker = None
        self.buttonStart.setText('开始检查')
        self.spinChallengeCount.setEnabled(True)

        if self.current_checking_plot_info:
            item = self.get_item(self.current_checking_plot_info)
            self.current_checking_plot_info.status = '失败'
            self.update_item(item, self.current_checking_plot_info)
            self.current_checking_plot_info = None

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

        index += 1
        item.setText(index, pi.path)
