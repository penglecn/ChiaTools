from PyQt5.QtWidgets import QWidget, QMessageBox, QMenu, QHBoxLayout, QCheckBox, QProgressBar, QStyleOptionButton, QStyle, QApplication
import core
from ui.PlotCheckWidget import Ui_PlotCheckWidget
from utils import get_official_chia_exe
from core.plot.check import PlotCheckManager, FolderInfo, PlotInfo
from typing import Optional, Tuple
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QTreeWidgetItem, QHeaderView
from PyQt5.Qt import QCursor, QStyle
from subprocess import run
import os
from config import get_config, save_config
from core.disk import disk_operation


class MyHeader(QHeaderView):
    isOn = False
    def __init__(self, orientation, parent=None):
        QHeaderView.__init__(self, orientation, parent)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        QHeaderView.paintSection(self, painter, rect, logicalIndex)
        painter.restore()

        if logicalIndex == 0:
            option = QStyleOptionButton()
            option.rect = QRect(10, 10, 10, 10)
            if self.isOn:
                option.state = QStyle.State_On
            else:
                option.state = QStyle.State_Off
            self.style().drawControl(QStyle.CE_CheckBox, option, painter)

    def mousePressEvent(self, event):
        self.isOn = not self.isOn
        self.updateSection(0)
        QHeaderView.mousePressEvent(self, event)


class PlotCheckWidget(QWidget, Ui_PlotCheckWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        # header_item: QTreeWidgetItem = QTreeWidgetItem()
        # header_item.setFlags(header_item.flags() | Qt.ItemIsUserCheckable)
        # header_item.data(1, Qt.CheckStateRole)
        # header_item.setCheckState(1, Qt.Checked)
        # header_item.setText(0, '333')
        # header_item.setText(1, '444')
        # self.treePlots.setHeaderItem(header_item)

        self.treePlots.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.treePlots.header().setStretchLastSection(False)
        self.treePlots.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treePlots.customContextMenuRequested.connect(self.on_show_menu)
        self.treePlots.setIndentation(20)

        self.spinChallengeCount.setVisible(False)
        self.labelChallengeCount.setVisible(False)
        self.spinBoxThreadCount.valueChanged.connect(self.on_change_thread_count)
        self.checkBoxCheckQuality.stateChanged.connect(self.on_check_quality)
        self.spinChallengeCount.valueChanged.connect(self.on_change_challenge_count)

        config = get_config()
        if 'check_thread_count' in config:
            self.spinBoxThreadCount.setValue(config['check_thread_count'])
        if 'check_quality' in config:
            self.checkBoxCheckQuality.setChecked(config['check_quality'])
        if 'check_challenge_count' in config:
            self.spinChallengeCount.setValue(config['check_challenge_count'])

        self.check_manager: PlotCheckManager = PlotCheckManager()
        self.check_manager.signalFoundPlot.connect(self.on_found_plot)
        self.check_manager.signalUpdateFolder.connect(self.on_update_folder)
        self.check_manager.signalUpdatePlot.connect(self.on_update_plot)
        self.check_manager.signalFinish.connect(self.on_finish)

        self.buttonStart.clicked.connect(self.on_start_check)
        self.buttonClear.clicked.connect(self.on_clear)

        self.load_folders()

        disk_operation.signalResult.connect(self.slotDiskOperation)

    def on_start_check(self):
        if self.check_manager.working:
            self.check_manager.stop()
            return

        folder_infos = self.get_checked_folder_infos()

        if not folder_infos:
            QMessageBox.information(self, '提示', '请先选择目录')
            return

        self.on_clear()

        self.buttonStart.setText('停止检查')
        self.spinBoxThreadCount.setEnabled(False)
        self.checkBoxCheckQuality.setEnabled(False)
        self.spinChallengeCount.setEnabled(False)
        self.buttonClear.setEnabled(False)

        self.check_manager.start(thread_count=self.spinBoxThreadCount.value(),
                                 folder_infos=folder_infos,
                                 check_quality=self.checkBoxCheckQuality.isChecked(),
                                 challenge_count=self.spinChallengeCount.value())

    def on_finish(self):
        self.buttonStart.setText('开始检查')
        self.spinBoxThreadCount.setDisabled(False)
        self.checkBoxCheckQuality.setDisabled(False)
        self.spinChallengeCount.setEnabled(self.checkBoxCheckQuality.isChecked())
        self.buttonClear.setEnabled(True)

    def on_change_thread_count(self):
        config = get_config()
        config['check_thread_count'] = self.spinBoxThreadCount.value()
        save_config()

    def on_check_quality(self):
        checked = self.checkBoxCheckQuality.isChecked()

        self.spinChallengeCount.setVisible(checked)
        self.labelChallengeCount.setVisible(checked)

        config = get_config()
        config['check_quality'] = checked
        save_config()

    def on_change_challenge_count(self):
        config = get_config()
        config['check_challenge_count'] = self.spinChallengeCount.value()
        save_config()

    def slotDiskOperation(self, name, opt):
        result = opt['result']

    def make_checkbox(self, slot, checked):
        widget = QWidget()
        layout = QHBoxLayout()
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        # checkbox.setDisabled(True)
        checkbox.setFixedWidth(30)
        if slot:
            checkbox.stateChanged.connect(slot)
        layout.addWidget(checkbox)
        layout.setAlignment(checkbox, Qt.AlignCenter)
        layout.setContentsMargins(5, 5, 5, 5)
        widget.setLayout(layout)

        return checkbox, widget

    def add_folder_item(self, folder):
        folder_item = QTreeWidgetItem()
        folder_item.setIcon(1, self.style().standardIcon(QStyle.SP_DirIcon))

        self.treePlots.addTopLevelItem(folder_item)

        mine_checkbox, mine_widget = self.make_checkbox(None, False)
        folder_item.setData(1, Qt.UserRole, mine_checkbox)
        self.treePlots.setItemWidget(folder_item, 0, mine_widget)

        progress = QProgressBar()
        self.treePlots.setItemWidget(folder_item, 5, progress)

        folder_info = FolderInfo()
        folder_info.folder = folder

        folder_item.setData(0, Qt.UserRole, folder_info)
        self.update_folder_item(folder_item, folder_info)

        return folder_item

    def remove_folder_item(self, folder):
        if self.check_manager.working:
            return

        folder_item, folder_info = self.get_folder_item_and_info(folder)

        if not folder_item:
            return

        self.treePlots.takeTopLevelItem(self.treePlots.indexOfTopLevelItem(folder_item))

    def load_folders(self):
        config = get_config()

        if 'hdd_folders' in config:
            hdd_folders_obj = config['hdd_folders']

            for folder_obj in hdd_folders_obj:
                folder = folder_obj['folder']

                self.add_folder_item(folder)

    def get_checked_folder_infos(self):
        folders = []
        for i in range(self.treePlots.topLevelItemCount()):
            item = self.treePlots.topLevelItem(i)
            checkbox: QCheckBox = item.data(1, Qt.UserRole)
            folder_info: FolderInfo = item.data(0, Qt.UserRole)
            if checkbox.isChecked():
                folders.append(folder_info)
        return folders

    def get_folder_item_and_info(self, folder) -> Tuple[Optional[QTreeWidgetItem], Optional[FolderInfo]]:
        for i in range(self.treePlots.topLevelItemCount()):
            item = self.treePlots.topLevelItem(i)
            fi: FolderInfo = item.data(0, Qt.UserRole)
            if fi.folder == folder:
                return item, fi
        return None, None

    def get_folder_item(self, folder_info: FolderInfo) -> Optional[QTreeWidgetItem]:
        for i in range(self.treePlots.topLevelItemCount()):
            item = self.treePlots.topLevelItem(i)
            fi: FolderInfo = item.data(0, Qt.UserRole)
            if fi.folder == folder_info.folder:
                return item
        return None

    def get_plot_item(self, folder_item: QTreeWidgetItem, plot_info: PlotInfo) -> Optional[QTreeWidgetItem]:
        for i in range(folder_item.childCount()):
            plot_item = folder_item.child(i)
            pi: PlotInfo = plot_item.data(0, Qt.UserRole)
            if pi == plot_info:
                return plot_item
        return None

    def update_folder_item(self, item: QTreeWidgetItem, folder_info: FolderInfo):
        col = 1
        item.setText(col, folder_info.folder)

        col += 1
        item.setText(col, f'{folder_info.checked_plot_count}/{folder_info.plot_count}')

        col = 5
        progress: QProgressBar = self.treePlots.itemWidget(item, col)
        progress.setValue(folder_info.progress)

    def update_plot_item(self, item: QTreeWidgetItem, plot_info: PlotInfo):
        col = 2
        item.setText(col, f'{plot_info.index}')

        col += 1
        item.setText(col, plot_info.status)

        col += 1
        item.setText(col, plot_info.quality)

        progress: QProgressBar = self.treePlots.itemWidget(item, 5)
        progress.setValue(plot_info.progress)

        col = 6
        item.setText(col, plot_info.filename)

        col += 1
        item.setText(col, plot_info.k)

        col += 1
        item.setText(col, plot_info.fpk)

        col += 1
        item.setText(col, plot_info.ppk)

        col += 1
        item.setText(col, plot_info.contract)

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

    def on_clear(self):
        self.check_manager.clear()
        for i in range(self.treePlots.topLevelItemCount()):
            folder_item: QTreeWidgetItem = self.treePlots.topLevelItem(i)
            folder_item.takeChildren()
            folder_info: FolderInfo = folder_item.data(0, Qt.UserRole)
            folder_info.clear()
            self.update_folder_item(folder_item, folder_info)

    def on_found_plot(self, folder_info: FolderInfo, plot_info: PlotInfo):
        folder_item = self.get_folder_item(folder_info)
        if folder_item is None:
            return

        plot_item = QTreeWidgetItem()
        plot_item.setData(0, Qt.UserRole, plot_info)
        folder_item.addChild(plot_item)

        progress = QProgressBar()
        self.treePlots.setItemWidget(plot_item, 5, progress)

        self.update_plot_item(plot_item, plot_info)
        self.update_folder_item(folder_item, folder_info)

    def on_update_folder(self, folder_info: FolderInfo):
        folder_item = self.get_folder_item(folder_info)
        if folder_item is None:
            return
        self.update_folder_item(folder_item, folder_info)

    def on_update_plot(self, plot_info: PlotInfo):
        folder_info: FolderInfo = plot_info.folder_info
        folder_item = self.get_folder_item(folder_info)
        if folder_item is None:
            return
        plot_item = self.get_plot_item(folder_item, plot_info)
        if plot_item is None:
            return
        self.update_folder_item(folder_item, folder_info)
        self.update_plot_item(plot_item, plot_info)
