from PyQt5.QtWidgets import QWidget, QMainWindow, QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressBar, \
    QMessageBox, QMenu, QCheckBox, QTreeWidgetItemIterator, QHBoxLayout
from PyQt5.Qt import pyqtSignal, QBrush, QColor, QModelIndex, QTimerEvent, QCursor
from PyQt5.QtCore import Qt
from ui.FoldersWidget import Ui_FoldersWidget
from config import save_config, get_config
from utils import size_to_str, delta_to_str, seconds_to_str
import psutil
import os
from core.disk import disk_operation


class FoldersWidget(QWidget, Ui_FoldersWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.main_window = None

        self.treeSSD.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.treeHDD.header().setSectionResizeMode(QHeaderView.ResizeToContents)

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
                self.addHDDFolder(folder_obj['folder'], folder_obj['mine'])
                self.updateHDDSpaces()

    def timerEvent(self, event: QTimerEvent) -> None:
        timer = event.timerId()

        if timer == self.timerIdUpdateSpace:
            self.updateSSDSpaces()
            self.updateHDDSpaces()

    def updateHDDSpaces(self):
        self.updateHDDDriverSpaces()
        self.updateHDDTotalSpaces()

    def updateSSDSpaces(self):
        self.updateSSDDriverSpaces()

    def addSSDFolder(self, folder):
        item = QTreeWidgetItem()
        item.setText(0, folder)
        self.treeSSD.addTopLevelItem(item)
        self.treeSSD.setItemWidget(item, 4, QProgressBar())

        self.updateSSDSpaces()

    def addHDDFolder(self, folder, checked):
        item = QTreeWidgetItem()
        item.setTextAlignment(0, Qt.AlignCenter)
        item.setText(1, folder)
        self.treeHDD.addTopLevelItem(item)

        widget = QWidget()
        layout = QHBoxLayout()
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(self.saveHDDFolderChecks)
        layout.addWidget(checkbox)
        layout.setAlignment(checkbox, Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setLayout(layout)

        item.setData(0, Qt.UserRole, checkbox)
        self.treeHDD.setItemWidget(item, 0, widget)
        self.treeHDD.setItemWidget(item, 6, QProgressBar())

        self.updateHDDSpaces()

    def saveHDDFolderChecks(self, i):
        hdd_folders = []
        for i in range(self.treeHDD.topLevelItemCount()):
            item = self.treeHDD.topLevelItem(i)
            checkbox: QCheckBox = item.data(0, Qt.UserRole)
            folder = item.text(1)
            hdd_folders.append({
                'folder': folder,
                'mine': checkbox.isChecked()
            })
        config = get_config()
        config['hdd_folders'] = hdd_folders
        save_config()

        self.restartMine()

        disk_operation.updateMiningPlotTotalInfo()

    def clickAddSSDFolder(self):
        folder = QFileDialog.getExistingDirectory()
        if not folder:
            return

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
        folder = QFileDialog.getExistingDirectory()
        if not folder:
            return

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
        })

        self.addHDDFolder(folder, True)

        save_config()

        self.restartMine()

        disk_operation.updateMiningPlotTotalInfo()

    def clickRemoveHDDFolder(self):
        indexes = self.treeHDD.selectedIndexes()
        if not indexes:
            return

        index = indexes[0]

        item = self.treeHDD.itemFromIndex(index)

        folder = item.text(1)

        self.treeHDD.takeTopLevelItem(index.row())

        config = get_config()

        for folder_obj in config['hdd_folders']:
            if folder_obj['folder'] == folder:
                config['hdd_folders'].remove(folder_obj)
                break

        save_config()

        self.restartMine()

        disk_operation.updateMiningPlotTotalInfo()

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
            for folder, usage in result.items():
                self.updateHDDItems(folder, usage)
        elif name == 'updateTotalSpaces':
            total_space = result['total_space']
            total_used = result['total_used']
            total_free = result['total_free']
            pi = result['plots_info']

            usage_status = f'总容量{size_to_str(total_space)}'
            usage_status += f' 使用容量{size_to_str(total_used)}'
            usage_status += f' 剩余容量{size_to_str(total_free)}'

            plots_status = f' 昨天文件数{pi["yesterday_count"]}个'
            plots_status += f' 今天文件数{pi["today_count"]}个'
            plots_status += f' 总文件数{pi["total_count"]}个'
            plots_status += f' 算力{size_to_str(pi["total_size"])}'

            self.labelHDDUsage.setText(usage_status)
            self.labelPlotsInfo.setText(plots_status)

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
        plots_info = usage['plots_info']

        column = 1
        item.setText(column, size_to_str(total))

        column += 1
        item.setText(column, size_to_str(used))

        column += 1
        item.setText(column, size_to_str(free))

        column += 1
        progress_bar: QProgressBar = self.treeSSD.itemWidget(item, column)
        progress_bar.setValue(percent)

    def updateHDDItems(self, folder, usage):
        item = None
        for i in range(self.treeHDD.topLevelItemCount()):
            _item: QTreeWidgetItem = self.treeHDD.topLevelItem(i)
            if _item.text(1) == folder:
                item = _item
                break

        if item is None:
            return

        used = usage['used']
        free = usage['free']
        total = usage['total']
        percent = usage['percent']
        plots_info = usage['plots_info']

        column = 2
        item.setText(column, size_to_str(total))

        column += 1
        item.setText(column, size_to_str(used))

        column += 1
        item.setText(column, size_to_str(free))

        column += 1
        item.setText(column, f'{plots_info["total_count"]}')

        column += 1
        progress_bar: QProgressBar = self.treeHDD.itemWidget(item, column)
        progress_bar.setValue(percent)

    def updateSSDDriverSpaces(self):
        folders = []
        for i in range(self.treeSSD.topLevelItemCount()):
            item = self.treeSSD.topLevelItem(i)
            folders.append(item.text(0))

        disk_operation.updateSSDDriverSpaces(folders)

    def updateHDDDriverSpaces(self):
        folders = []
        for i in range(self.treeHDD.topLevelItemCount()):
            item = self.treeHDD.topLevelItem(i)
            folders.append(item.text(1))

        disk_operation.updateHDDDriverSpaces(folders)

    def updateHDDTotalSpaces(self):
        folders = []

        count = self.treeHDD.topLevelItemCount()
        for i in range(count):
            item = self.treeHDD.topLevelItem(i)
            folder = item.text(1)
            folders.append(folder)

        disk_operation.updateTotalSpaces(folders)
