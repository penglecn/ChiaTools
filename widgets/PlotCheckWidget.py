from PyQt5.QtWidgets import QWidget, QMessageBox, QMenu, QHBoxLayout, QCheckBox, QProgressBar, QStyleOptionButton, QStyle, QApplication, QPushButton
import core
from ui.PlotCheckWidget import Ui_PlotCheckWidget
from utils import get_official_chia_exe
from core.plot.check import PlotCheckManager, FolderInfo, PlotInfo
from typing import Optional, Tuple
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QTreeWidgetItem, QHeaderView
from PyQt5.Qt import QCursor, QStyle, QBrush, QColor
from subprocess import run
import os
from config import get_config, save_config
from core.disk import disk_operation


def make_checkbox(slot, checked):
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


class CustomHeaderView(QHeaderView):
    def __init__(self, orientation, parent=None):
        super(CustomHeaderView, self).__init__(orientation, parent)

        widget = QWidget(self)
        layout = QHBoxLayout()
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox)
        layout.setAlignment(self.checkbox, Qt.AlignHCenter)
        layout.setContentsMargins(25, 6, 5, 5)
        widget.setLayout(layout)


class CustomTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, parent=None):
        QTreeWidgetItem.__init__(self, parent)

    def __lt__(self, other):
        column = self.treeWidget().sortColumn()

        if column in [2, 4]:
            try:
                v1 = float(self.text(column))
                v2 = float(other.text(column))
                return v1 < v2
            except ValueError:
                pass

        return super().__lt__(other)


class PlotCheckWidget(QWidget, Ui_PlotCheckWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.header: CustomHeaderView = CustomHeaderView(Qt.Horizontal, self.treePlots)
        self.treePlots.setHeader(self.header)

        self.header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.header.setStretchLastSection(False)
        self.header.checkbox.stateChanged.connect(self.on_check_all)

        self.treePlots.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treePlots.customContextMenuRequested.connect(self.on_show_menu)
        self.treePlots.setIndentation(20)
        self.treePlots.headerItem().setText(0, '         ')

        self.spinChallengeCount.setVisible(False)
        self.labelChallengeCount.setVisible(False)
        self.spinBoxMaxThreadCount.valueChanged.connect(self.on_change_max_thread_count)
        self.checkBoxCheckQuality.stateChanged.connect(self.on_check_quality)
        self.spinChallengeCount.valueChanged.connect(self.on_change_challenge_count)

        config = get_config()
        if 'check_max_thread_count' in config:
            self.spinBoxMaxThreadCount.setValue(config['check_max_thread_count'])
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
        self.buttonClear.clicked.connect(self.on_clear_all)

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

        self.on_clear_checked()

        self.buttonStart.setText('停止检查')
        self.spinBoxMaxThreadCount.setEnabled(False)
        self.checkBoxCheckQuality.setEnabled(False)
        self.spinChallengeCount.setEnabled(False)
        self.buttonClear.setEnabled(False)

        self.check_manager.start(max_thread_count=self.spinBoxMaxThreadCount.value(),
                                 folder_infos=folder_infos,
                                 check_quality=self.checkBoxCheckQuality.isChecked(),
                                 challenge_count=self.spinChallengeCount.value())

        self.update_checkbox_enable(False)

    def on_finish(self):
        self.buttonStart.setText('开始检查')
        self.spinBoxMaxThreadCount.setDisabled(False)
        self.checkBoxCheckQuality.setDisabled(False)
        self.spinChallengeCount.setDisabled(False)
        self.buttonClear.setEnabled(True)

        self.update_checkbox_enable(True)

    def update_checkbox_enable(self, enable=None):
        if enable is None:
            enable = not self.check_manager.working

        self.header.checkbox.setEnabled(enable)

        for i in range(self.treePlots.topLevelItemCount()):
            item: QTreeWidgetItem = self.treePlots.topLevelItem(i)
            checkbox: QCheckBox = item.data(1, Qt.UserRole)
            checkbox.setEnabled(enable)

    def on_check_all(self):
        checked = self.header.checkbox.isChecked()

        for i in range(self.treePlots.topLevelItemCount()):
            item: QTreeWidgetItem = self.treePlots.topLevelItem(i)
            checkbox: QCheckBox = item.data(1, Qt.UserRole)
            checkbox.setChecked(checked)

    def on_change_max_thread_count(self):
        config = get_config()
        config['check_max_thread_count'] = self.spinBoxMaxThreadCount.value()
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

    def add_folder_item(self, folder, manual=False):
        folder_item = CustomTreeWidgetItem()
        folder_item.setIcon(1, self.style().standardIcon(QStyle.SP_DirIcon))

        self.treePlots.addTopLevelItem(folder_item)

        checked = True
        if self.check_manager.working:
            checked = False
        mine_checkbox, mine_widget = make_checkbox(None, checked)
        folder_item.setData(1, Qt.UserRole, mine_checkbox)
        self.treePlots.setItemWidget(folder_item, 0, mine_widget)

        mine_checkbox.stateChanged.connect(self.on_check_item)

        progress = QProgressBar()
        self.treePlots.setItemWidget(folder_item, 5, progress)

        folder_info = FolderInfo()
        folder_info.folder = folder

        folder_item.setData(0, Qt.UserRole, folder_info)
        self.update_folder_item(folder_item, folder_info)

        self.update_checkbox_enable()

        return folder_item

    def on_check_item(self):
        all_checked = True
        for i in range(self.treePlots.topLevelItemCount()):
            item: QTreeWidgetItem = self.treePlots.topLevelItem(i)
            if not self.is_folder_item_checked(item):
                all_checked = False
                break
        self.header.checkbox.stateChanged.disconnect()
        self.header.checkbox.setChecked(all_checked)
        self.header.checkbox.stateChanged.connect(self.on_check_all)

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

        self.treePlots.sortByColumn(1, Qt.AscendingOrder)

    def get_checked_folder_infos(self):
        folders = []
        for i in range(self.treePlots.topLevelItemCount()):
            item = self.treePlots.topLevelItem(i)
            folder_info: FolderInfo = item.data(0, Qt.UserRole)
            if self.is_folder_item_checked(item):
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

    def update_folder_item(self, item: QTreeWidgetItem, folder_info: Optional[FolderInfo]):
        if folder_info is None:
            folder_info = item.data(0, Qt.UserRole)

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
        item.setBackground(col, QBrush(QColor('#ffffff')))
        item.setForeground(col, QBrush(QColor(0, 0, 0)))
        if plot_info.finish:
            if plot_info.success:
                color = QColor('#50c350')
            else:
                color = QColor('#e86363')
            item.setBackground(col, QBrush(color))
            item.setForeground(col, QBrush(QColor(255, 255, 255)))
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

    def on_show_menu(self, pos):
        items: [QTreeWidgetItem] = self.treePlots.selectedItems()

        if not items:
            return

        plots = []

        for plot_item in items:
            folder_item = plot_item.parent()
            if folder_item is None:
                return

            fi = folder_item.data(0, Qt.UserRole)
            pi = plot_item.data(0, Qt.UserRole)
            plots.append(({
                'folder_item': folder_item,
                'plot_item': plot_item,
                'fi': fi,
                'pi': pi,
            }))

        menu = QMenu(self)

        action_locate = None
        action_delete = None

        if len(items) == 1:
            action_locate = menu.addAction(u"浏览文件")

        if not self.check_manager.working:
            action_delete = menu.addAction(u"删除")

        action = menu.exec(QCursor.pos())

        if not action:
            return

        if action == action_locate:
            run('explorer /select, ' + plots[0]['pi'].path)
        elif action == action_delete:
            if QMessageBox.information(self, '提示', f"确定要删除这{len(plots)}个文件吗？\n删除后将无法恢复。",
                                       QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return
            for obj in plots:
                folder_item: QTreeWidgetItem = obj['folder_item']
                plot_item: QTreeWidgetItem = obj['plot_item']
                pi: PlotInfo = obj['pi']
                fi: FolderInfo = obj['fi']
                try:
                    os.remove(pi.path)
                except:
                    if not core.is_debug():
                        QMessageBox.information(self, '提示', f"删除文件失败\n{pi.path}\n请检查文件是否被占用。")
                        return
                folder_item.takeChild(folder_item.indexOfChild(plot_item))
                fi.plots.remove(pi)

                self.update_folder_item(folder_item, None)

    def on_clear_all(self):
        self.check_manager.clear()
        for i in range(self.treePlots.topLevelItemCount()):
            folder_item: QTreeWidgetItem = self.treePlots.topLevelItem(i)
            folder_item.takeChildren()
            folder_info: FolderInfo = folder_item.data(0, Qt.UserRole)
            folder_info.clear()
            self.update_folder_item(folder_item, folder_info)

    def on_clear_checked(self):
        self.check_manager.clear()
        for i in range(self.treePlots.topLevelItemCount()):
            folder_item: QTreeWidgetItem = self.treePlots.topLevelItem(i)
            if not self.is_folder_item_checked(folder_item):
                continue
            folder_item.takeChildren()
            folder_info: FolderInfo = folder_item.data(0, Qt.UserRole)
            folder_info.clear()
            self.update_folder_item(folder_item, folder_info)

    def is_folder_item_checked(self, item: QTreeWidgetItem):
        checkbox: QCheckBox = item.data(1, Qt.UserRole)
        return checkbox.isChecked()

    def on_found_plot(self, folder_info: FolderInfo, plot_info: PlotInfo):
        folder_item = self.get_folder_item(folder_info)
        if folder_item is None:
            return

        plot_item = CustomTreeWidgetItem()
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
