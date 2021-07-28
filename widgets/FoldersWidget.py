from PyQt5.QtWidgets import QWidget, QMainWindow, QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressBar, \
    QMessageBox, QMenu, QCheckBox, QTreeWidgetItemIterator, QHBoxLayout
from PyQt5.Qt import pyqtSignal, QBrush, QColor, QModelIndex, QTimerEvent, QCursor, QStyle, QSettings
from PyQt5.QtCore import Qt

import core
from ui.FoldersWidget import Ui_FoldersWidget
from config import save_config, get_config
from utils import size_to_str, delta_to_str, seconds_to_str
import psutil
import os
from core.disk import disk_operation
from typing import Optional


class FoldersWidget(QWidget, Ui_FoldersWidget):
    LastDirectory = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.main_window = None

        self.treeSSD.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.treeHDD.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.treeHDD.sortByColumn(0, Qt.AscendingOrder)

        self.loadFolders()

        self.buttonAddSSDFolder.clicked.connect(self.clickAddSSDFolder)
        self.buttonRemoveSSDFolder.clicked.connect(self.clickRemoveSSDFolder)
        self.buttonAddHDDFolder.clicked.connect(self.clickAddHDDFolder)
        self.buttonRemoveHDDFolder.clicked.connect(self.clickRemoveHDDFolder)

        self.timerIdUpdateSpace = self.startTimer(1000 * 10)

        disk_operation.signalResult.connect(self.slotDiskOperation)

    def setMainWindow(self, win):
        self.main_window = win

        disk_operation.updateMiningPlotTotalInfo()

    def loadFolders(self):
        config = get_config()

        if 'ssd_folders' in config:
            ssd_folders = config['ssd_folders']

            for folder in ssd_folders:
                self.addSSDFolder(folder)

            self.updateSSDSpaces()

        if 'hdd_folders' in config:
            hdd_folders_obj = config['hdd_folders']

            for folder_obj in hdd_folders_obj:
                self.addHDDFolder(folder_obj['folder'], folder_obj['mine'], folder_obj['new_plot'])
                self.updateHDDSpaces()

    def getHDDDrivers(self):
        drivers = []

        for i in range(self.treeHDD.topLevelItemCount()):
            driver_item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
            drivers.append(driver_item.text(0))

        return drivers

    def getSSDFolders(self):
        folders = []

        for i in range(self.treeSSD.topLevelItemCount()):
            driver_item: QTreeWidgetItem = self.treeSSD.topLevelItem(i)
            folders.append(driver_item.text(0))

        return folders

    def getHDDFolders(self):
        folders = []

        for i in range(self.treeHDD.topLevelItemCount()):
            driver_item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
            for j in range(driver_item.childCount()):
                folder_item = driver_item.child(j)
                folders.append(folder_item.text(0))

        return folders

    def timerEvent(self, event: QTimerEvent) -> None:
        timer = event.timerId()

        if timer == self.timerIdUpdateSpace:
            self.updateSSDSpaces()
            self.updateHDDSpaces()

    def updateHDDSpaces(self):
        self.updateHDDDriverSpaces()
        self.updateHDDTotalSpaces()
        self.updateFolderPlotCount()

    def updateSSDSpaces(self):
        self.updateSSDDriverSpaces()

    def addSSDFolder(self, folder):
        item = QTreeWidgetItem()
        item.setText(0, folder)
        item.setIcon(0, self.style().standardIcon(QStyle.SP_DriveHDIcon))
        self.treeSSD.addTopLevelItem(item)
        self.treeSSD.setItemWidget(item, 4, QProgressBar())

        self.updateSSDSpaces()

    def addHDDFolder(self, folder, mine, new_plot):
        driver, _ = os.path.splitdrive(folder)

        if not driver:
            return

        driver_item: Optional[QTreeWidgetItem] = None

        for i in range(self.treeHDD.topLevelItemCount()):
            _item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
            _item_driver = _item.text(0)
            if _item_driver == driver:
                driver_item = _item
                break

        if not driver_item:
            driver_item = QTreeWidgetItem()
            driver_item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
            driver_item.setText(0, driver)

            driver_item.setIcon(0, self.style().standardIcon(QStyle.SP_DriveHDIcon))

            self.treeHDD.addTopLevelItem(driver_item)

            self.treeHDD.setItemWidget(driver_item, 7, QProgressBar())

        folder_item = QTreeWidgetItem()
        folder_item.setTextAlignment(0, Qt.AlignLeft | Qt.AlignVCenter)
        folder_item.setText(0, folder)
        folder_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))

        driver_item.addChild(folder_item)
        driver_item.setExpanded(True)

        def make_checkbox(slot, checked):
            widget = QWidget()
            layout = QHBoxLayout()
            checkbox = QCheckBox()
            checkbox.setChecked(checked)
            checkbox.stateChanged.connect(slot)
            layout.addWidget(checkbox)
            layout.setAlignment(checkbox, Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)

            return checkbox, widget

        mine_checkbox, mine_widget = make_checkbox(self.saveHDDFolderChecks, mine)
        folder_item.setData(1, Qt.UserRole, mine_checkbox)
        self.treeHDD.setItemWidget(folder_item, 1, mine_widget)

        new_plot_checkbox, new_plot_widget = make_checkbox(self.saveHDDFolderChecks, new_plot)
        folder_item.setData(2, Qt.UserRole, new_plot_checkbox)
        self.treeHDD.setItemWidget(folder_item, 2, new_plot_widget)

        self.treeHDD.sortByColumn(0, Qt.AscendingOrder)

        self.updateHDDSpaces()

    def saveHDDFolderChecks(self, i):
        hdd_folders = []
        for i in range(self.treeHDD.topLevelItemCount()):
            driver_item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
            for j in range(driver_item.childCount()):
                folder_item = driver_item.child(j)
                mine_checkbox: QCheckBox = folder_item.data(1, Qt.UserRole)
                new_plot_checkbox: QCheckBox = folder_item.data(2, Qt.UserRole)
                folder = folder_item.text(0)
                hdd_folders.append({
                    'folder': folder,
                    'mine': mine_checkbox.isChecked(),
                    'new_plot': new_plot_checkbox.isChecked()
                })
        config = get_config()
        config['hdd_folders'] = hdd_folders
        save_config()

        self.restartMine()

        disk_operation.updateMiningPlotTotalInfo()

    def clickAddSSDFolder(self):
        folder = QFileDialog.getExistingDirectory(directory=FoldersWidget.LastDirectory)
        if not folder:
            return

        FoldersWidget.LastDirectory = folder

        config = get_config()

        if 'ssd_folders' not in config:
            config['ssd_folders'] = []

        if folder in config['ssd_folders']:
            QMessageBox.information(self, '提示', f'目录{folder}已经存在')
            return

        config['ssd_folders'].append(folder)

        self.addSSDFolder(folder)

        save_config()

    def clickRemoveSSDFolder(self):
        indexes = self.treeSSD.selectedIndexes()
        if not indexes:
            return

        index = indexes[0]

        item = self.treeSSD.itemFromIndex(index)

        folder = item.text(0)

        self.treeSSD.takeTopLevelItem(index.row())

        config = get_config()

        if folder not in config['ssd_folders']:
            return

        config['ssd_folders'].remove(folder)

        save_config()

    def clickAddHDDFolder(self):
        folder = QFileDialog.getExistingDirectory(directory=FoldersWidget.LastDirectory)
        if not folder:
            return

        FoldersWidget.LastDirectory = folder

        config = get_config()

        if 'hdd_folders' not in config:
            config['hdd_folders'] = []

        for hdd_folder in config['hdd_folders']:
            if folder == hdd_folder['folder']:
                QMessageBox.information(self, '提示', f'目录{folder}已经存在')
                return

        config['hdd_folders'].append({
            'folder': folder,
            'mine': True,
            'new_plot': True,
        })

        self.addHDDFolder(folder, True, True)

        save_config()

        self.restartMine()

        disk_operation.updateMiningPlotTotalInfo()

    def clickRemoveHDDFolder(self):
        indexes = self.treeHDD.selectedIndexes()
        if not indexes:
            return

        index = indexes[0]

        item: QTreeWidgetItem = self.treeHDD.itemFromIndex(index)
        parent: QTreeWidgetItem = item.parent()

        is_root = parent is None

        folders_to_remove = []

        if is_root:
            for i in range(item.childCount()):
                folder_item = item.child(i)
                folders_to_remove.append(folder_item.text(0))
            self.treeHDD.takeTopLevelItem(index.row())
        else:
            folders_to_remove.append(item.text(0))
            parent.takeChild(parent.indexOfChild(item))
            if parent.childCount() == 0:
                self.treeHDD.takeTopLevelItem(self.treeHDD.indexOfTopLevelItem(parent))

        self.treeHDD.sortByColumn(0, Qt.AscendingOrder)

        config = get_config()

        for folder_to_remove in folders_to_remove:
            for folder_obj in config['hdd_folders']:
                if folder_obj['folder'] == folder_to_remove:
                    config['hdd_folders'].remove(folder_obj)
                    break

        save_config()

        self.restartMine()

        disk_operation.updateMiningPlotTotalInfo()
        self.updateFolderPlotCount()

    def restartMine(self, log=''):
        if not self.main_window:
            return

        self.main_window.tabHPoolMineWidget.restartMine(log)
        self.main_window.tabHuobiPoolMineWidget.restartMine(log)

    def slotDiskOperation(self, name, opt):
        result = opt['result']

        if name == 'updateSSDDriverSpaces':
            for folder, usage in result.items():
                self.updateSSDItems(folder, usage)
        elif name == 'updateHDDDriverSpaces':
            self.updateHDDDriverItems(result.items())
        elif name == 'updateFolderPlotCount':
            self.updateHDDFolderItems(result['folders_plot_info'])
        elif name == 'updateTotalSpaces':
            driver_count = result['driver_count']
            total_space = result['total_space']
            total_used = result['total_used']
            total_free = result['total_free']
            pi = result['plots_info']

            usage_status = f'硬盘数{driver_count}个'
            usage_status += f' 总容量{size_to_str(total_space)}'
            usage_status += f' 使用容量{size_to_str(total_used)}'
            usage_status += f' 剩余容量{size_to_str(total_free)}'

            plots_status = f' 昨天文件数{pi["yesterday_count"]}个'
            plots_status += f' 今天文件数{pi["today_count"]}个'
            plots_status += f' 总文件数{pi["total_count"]}个'
            plots_status += f' 算力{size_to_str(pi["total_size"])}'

            self.labelHDDUsage.setText(usage_status)
            self.labelPlotsInfo.setText(plots_status)

    def getHDDDriverItem(self, driver):
        for i in range(self.treeHDD.topLevelItemCount()):
            driver_item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
            if driver_item.text(0) == driver:
                return driver_item
        return None

    def getHDDFolderItem(self, folder):
        for i in range(self.treeHDD.topLevelItemCount()):
            driver_item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
            for j in range(driver_item.childCount()):
                folder_item = driver_item.child(j)
                if folder_item.text(0) == folder:
                    return folder_item
        return None

    def updateSSDItems(self, folder, usage):
        item = None
        for i in range(self.treeSSD.topLevelItemCount()):
            _item: QTreeWidgetItem = self.treeSSD.topLevelItem(i)
            if _item.text(0) == folder:
                item = _item
                break

        if item is None:
            return

        used = usage['used']
        free = usage['free']
        total = usage['total']
        percent = usage['percent']

        column = 1
        item.setText(column, size_to_str(total))

        column += 1
        item.setText(column, size_to_str(used))

        column += 1
        item.setText(column, size_to_str(free))

        column += 1
        progress_bar: QProgressBar = self.treeSSD.itemWidget(item, column)
        progress_bar.setValue(percent)

    def updateHDDDriverItems(self, drivers):
        for driver, usage in drivers:
            driver_item: Optional[QTreeWidgetItem] = None
            for i in range(self.treeHDD.topLevelItemCount()):
                _item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
                if _item.text(0) == driver:
                    driver_item = _item
                    break

            if driver_item is None:
                continue

            self.updateHDDDriverItem(driver_item, usage)

    def updateHDDItems(self, folders):
        drivers = {}

        for folder, usage in folders:
            driver, _ = os.path.splitdrive(folder)
            if driver not in drivers:
                drivers[driver] = []
            drivers[driver].append((folder, usage))

        for driver, folders in enumerate(drivers):
            driver_item: Optional[QTreeWidgetItem] = None
            for i in range(self.treeHDD.topLevelItemCount()):
                _item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
                if _item.text(0) == driver:
                    driver_item = _item
                    break

            if driver_item is None:
                continue

            for info in folders:
                folder, usage = info
                folder_item = None
                for i in range(driver_item.childCount()):
                    _item: QTreeWidgetItem = driver_item.child(i)
                    if _item.text(0) == folder:
                        folder_item = _item
                        break

                if folder_item is None:
                    continue

                self.updateHDDItem(folder_item, usage)

    def updateHDDDriverItem(self, item: QTreeWidgetItem, usage):
        used = usage['used']
        free = usage['free']
        total = usage['total']
        percent = usage['percent']

        column = 3
        item.setText(column, size_to_str(total))

        column += 1
        item.setText(column, size_to_str(used))

        column += 1
        item.setText(column, size_to_str(free))

        column += 2
        progress_bar: QProgressBar = self.treeHDD.itemWidget(item, column)
        progress_bar.setValue(percent)

    def updateHDDFolderItems(self, folders_plot_info):
        drivers = {}

        for folder in folders_plot_info:
            info = folders_plot_info[folder]
            driver = os.path.splitdrive(folder)
            if driver:
                driver = driver[0]
            if driver not in drivers:
                drivers[driver] = []
            drivers[driver].append((folder, info))

        for driver in drivers:
            folders = drivers[driver]
            driver_item = self.getHDDDriverItem(driver)
            if not driver_item:
                continue
            driver_total_count = 0
            for folder, info in folders:
                folder_item = self.getHDDFolderItem(folder)
                if not folder_item:
                    continue
                self.updateHDDFolderItem(folder_item, info)
                driver_total_count += info['total_count']
            driver_item.setText(6, f'{driver_total_count}')

    def updateHDDFolderItem(self, item: QTreeWidgetItem, info):
        item.setText(6, f'{info["total_count"]}')

    def updateSSDDriverSpaces(self):
        folders = self.getSSDFolders()
        disk_operation.updateSSDDriverSpaces(folders)

    def updateHDDDriverSpaces(self):
        disk_operation.updateHDDDriverSpaces(self.getHDDDrivers())

    def updateHDDTotalSpaces(self):
        disk_operation.updateTotalSpaces(self.getHDDDrivers(), self.getHDDFolders())

    def updateFolderPlotCount(self):
        disk_operation.updateFolderPlotCount(self.getHDDFolders())
