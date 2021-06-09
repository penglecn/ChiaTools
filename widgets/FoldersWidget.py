from PyQt5.QtWidgets import QWidget, QMainWindow, QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressBar, \
    QMessageBox, QMenu, QCheckBox, QTreeWidgetItemIterator
from PyQt5.Qt import pyqtSignal, QBrush, QColor, QModelIndex, QTimerEvent, QCursor
from PyQt5.QtCore import Qt
from ui.FoldersWidget import Ui_FoldersWidget
from config import save_config, get_config
from utils import size_to_str, delta_to_str, seconds_to_str
import psutil
import os
from core.disk import DiskOperation


class FoldersWidget(QWidget, Ui_FoldersWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.disk_operation = DiskOperation()
        self.main_window = None

        self.treeSSD.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.treeHDD.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.loadFolders()

        self.buttonAddSSDFolder.clicked.connect(self.clickAddSSDFolder)
        self.buttonRemoveSSDFolder.clicked.connect(self.clickRemoveSSDFolder)
        self.buttonAddHDDFolder.clicked.connect(self.clickAddHDDFolder)
        self.buttonRemoveHDDFolder.clicked.connect(self.clickRemoveHDDFolder)

        self.timerIdUpdateSpace = self.startTimer(1000 * 10)

        self.disk_operation.signalResult.connect(self.slotDiskOperation)
        self.disk_operation.start()

    def setMainWindow(self, win):
        self.main_window = win

        self.main_window.tabHPoolMineWidget.updateTotalGB()

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
        self.updateDriverSpaces(self.treeHDD, 1)
        self.updateTotalSpaces(self.treeHDD, 1)

    def updateSSDSpaces(self):
        self.updateDriverSpaces(self.treeSSD)

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

        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.stateChanged.connect(self.saveHDDFolderChecks)
        self.treeHDD.setItemWidget(item, 0, checkbox)
        self.treeHDD.setItemWidget(item, 5, QProgressBar())

        self.updateHDDSpaces()

    def saveHDDFolderChecks(self, i):
        hdd_folders = []
        for i in range(self.treeHDD.topLevelItemCount()):
            item = self.treeHDD.topLevelItem(i)
            checkbox: QCheckBox = self.treeHDD.itemWidget(item, 0)
            folder = item.text(1)
            hdd_folders.append({
                'folder': folder,
                'mine': checkbox.isChecked()
            })
        config = get_config()
        config['hdd_folders'] = hdd_folders
        save_config()

        self.main_window.tabHPoolMineWidget.restartMine()
        self.main_window.tabHPoolMineWidget.updateTotalGB()

    def clickAddSSDFolder(self):
        folder = QFileDialog.getExistingDirectory()
        if not folder:
            return

        config = get_config()

        if 'ssd_folders' not in config:
            config['ssd_folders'] = []
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
        config['hdd_folders'].append({
            'folder': folder,
            'mine': True,
        })

        self.addHDDFolder(folder, True)

        save_config()

        self.main_window.tabHPoolMineWidget.restartMine()
        self.main_window.tabHPoolMineWidget.updateTotalGB()

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

        self.main_window.tabHPoolMineWidget.restartMine()
        self.main_window.tabHPoolMineWidget.updateTotalGB()

    def slotDiskOperation(self, name, opt):
        result = opt['result']

        if name == 'updateDriverSpaces':
            column_offset = opt['column_offset']
            tree: QTreeWidget = opt['tree']

            for folder, usage in result.items():
                item: QTreeWidgetItem = None
                for i in range(tree.topLevelItemCount()):
                    _item: QTreeWidgetItem = tree.topLevelItem(i)
                    if _item.text(column_offset) == folder:
                        item = _item
                        break

                if item is None:
                    continue

                used = usage['used']
                free = usage['free']
                total = usage['total']
                percent = usage['percent']

                column = column_offset + 1
                item.setText(column, size_to_str(used))

                column += 1
                item.setText(column, size_to_str(free))

                column += 1
                item.setText(column, size_to_str(total))

                column += 1
                progress_bar: QProgressBar = tree.itemWidget(item, column)
                progress_bar.setValue(percent)
        elif name == 'updateTotalSpaces':
            total_space = result['total_space']
            total_used = result['total_used']
            total_free = result['total_free']

            self.labelTotalSpace.setText(f'{size_to_str(total_space)}')
            self.labelTotalUsed.setText(f'{size_to_str(total_used)}')
            self.labelTotalFree.setText(f'{size_to_str(total_free)}')

    def updateDriverSpaces(self, tree: QTreeWidget, column_offset=0):
        folders = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            folders.append(item.text(column_offset))

        self.disk_operation.add_operation('updateDriverSpaces', {
            'tree': tree,
            'folders': folders,
            'column_offset': column_offset,
        })

    def updateTotalSpaces(self, tree: QTreeWidget, column_offset=0):
        folders = []

        count = tree.topLevelItemCount()
        for i in range(count):
            item = tree.topLevelItem(i)
            folder = item.text(column_offset)
            folders.append(folder)

        self.disk_operation.add_operation('updateTotalSpaces', {
            'folders': folders,
        })
