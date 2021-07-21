import psutil
from PyQt5.QtWidgets import QDialog, QMessageBox, QTreeWidgetItem, QHeaderView, QStyle
from PyQt5.QtCore import Qt
from ui.CreatePlotDialog import Ui_CreatePlotDialog
from core.plot import PlotTask, PlotSubTask
from config import get_config, save_config
import os
from utils import make_name, size_to_str, get_k_size, get_k_temp_size, get_official_chia_exe, \
    seconds_to_str, is_chia_support_new_protocol
from datetime import datetime
from core.disk import get_disk_usage
from PyQt5.QtWidgets import QFileDialog
from core import BASE_DIR, is_debug
from core.wallet import wallet_manager
import platform
from typing import Optional
from core.plotter import PLOTTER_OFFICIAL, PLOTTER_BUILTIN, PLOTTER_CHIA_PLOT


class CreatePlotDialog(QDialog, Ui_CreatePlotDialog):
    last_ssd_folder = ''
    last_hdd_folder = ''
    selected_temp2_folders = []
    wallets = {}

    def __init__(self, task: Optional[PlotTask] = None, auto=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.pushReloadWallets.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))

        self.result = []
        self.task = None
        self.batch_tasks = []
        self.current_buckets = 128
        self.current_chia_plot_buckets = 256
        self.custom_fpk = ''
        self.custom_ppk = ''
        self.custom_nft = ''

        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.treeWidgetTasks.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        config = get_config()

        self.buttonBox.button(self.buttonBox.Ok).setText('创建')
        self.buttonBox.button(self.buttonBox.Cancel).setText('取消')
        self.checkBoxSpecifyCount.stateChanged.connect(self.check_specify_count)
        self.spinNumber.valueChanged.connect(self.update_tip_text)
        self.pushReloadWallets.clicked.connect(self.reload_wallets)
        self.labelReloadingWallets.setVisible(False)
        wallet_manager.signalGetWallets.connect(self.slot_get_wallets)

        self.comboK.addItem('101.4GiB (k=32, 临时文件: 239GiB)', 32)
        self.comboK.addItem('208.8GiB (k=33, 临时文件: 521GiB)', 33)
        self.comboK.addItem('429.8GiB (k=34, 临时文件: 1041GiB)', 34)
        self.comboK.addItem('884.1GiB (k=35, 临时文件: 2175GiB)', 35)
        self.comboK.setCurrentIndex(0)

        self.comboBucketNum.addItem('16', 16)
        self.comboBucketNum.addItem('32', 32)
        self.comboBucketNum.addItem('64', 64)
        self.comboBucketNum.addItem('128', 128)
        self.comboBucketNum.setCurrentIndex(self.comboBucketNum.count()-1)

        chia_plot_exe = self.get_chia_plot_exe()
        self.comboCmdLine.addItem('使用多线程chia_plot.exe', chia_plot_exe)
        self.comboCmdLine.setCurrentIndex(0)
        self.lineEditCmdLine.setText(chia_plot_exe)

        # self.comboCmdLine.addItem('使用内置ProofOfSpace.exe', self.get_builtin_exe())

        self.chia_exe, self.chia_ver = get_official_chia_exe()
        if self.chia_exe:
            self.comboCmdLine.addItem('使用钱包chia.exe', self.chia_exe)
        else:
            CreatePlotDialog.wallets = {}
        self.load_wallets()

        wallets = CreatePlotDialog.wallets

        if 'buckets' in config:
            self.current_buckets = config['buckets']

        if 'chia_plot_buckets' in config:
            self.current_chia_plot_buckets = config['chia_plot_buckets']

        self.load_temp2()
        self.checkBoxSpecifyTemp2.stateChanged.connect(self.slot_check_temp2)
        self.comboTemp2.setDisabled(True)

        def select_cmdline(cmdline):
            for i in range(self.comboCmdLine.count()):
                d = self.comboCmdLine.itemData(i, Qt.UserRole)
                if d == cmdline:
                    self.comboCmdLine.setCurrentIndex(i)
                    return

            if task:
                self.comboCmdLine.addItem(os.path.basename(cmdline), cmdline)
                self.comboCmdLine.setCurrentIndex(self.comboCmdLine.count()-1)
                self.lineEditCmdLine.setText(cmdline)

        def select_k_combo(k):
            for i in range(self.comboK.count()):
                d = self.comboK.itemData(i, Qt.UserRole)
                if d == k:
                    self.comboK.setCurrentIndex(i)
                    return

        self.modify = False

        if task:
            self.task = task
            self.modify = True

            self.comboCmdLine.setDisabled(True)

            self.comboSSD.addItem(task.ssd_folder, task.ssd_folder)
            self.comboSSD.setDisabled(True)

            self.load_hdd(last_folder='' if self.task.auto_hdd_folder else task.hdd_folder)

            self.select_wallet(task.fpk, task.ppk, task.nft)
            self.change_wallet()
            self.comboWallet.setDisabled(True)
            self.labelReloadingWallets.setVisible(False)
            self.pushReloadWallets.setVisible(False)
            self.editFpk.setPlainText(task.fpk)
            self.editFpk.setDisabled(True)
            self.editPpk.setPlainText(task.ppk)
            self.editPpk.setDisabled(True)
            self.editNft.setPlainText(task.nft)
            self.editNft.setDisabled(True)

            self.checkBoxSpecifyCount.setChecked(task.specify_count)
            self.checkBoxSpecifyCount.setDisabled(True)
            self.spinNumber.setValue(task.count)
            self.spinNumber.setDisabled(True)

            self.spinThreadNum.setValue(task.number_of_thread)
            self.spinMemory.setValue(task.memory_size)

            self.timeEditDelay.setDisabled(True)

            if task.cmdline == self.get_chia_plot_exe():
                self.current_chia_plot_buckets = task.buckets
            else:
                self.current_buckets = task.buckets

            select_k_combo(task.k)
            self.checkBoxNoBitfield.setChecked(task.nobitfield)
            select_cmdline(task.cmdline)

            if task.temporary2_folder:
                self.checkBoxSpecifyTemp2.setChecked(True)
                self.select_temp2(task.temporary2_folder)

            self.setWindowTitle('编辑P图任务')

            self.buttonBox.button(self.buttonBox.Ok).setText('修改')
        else:
            self.comboSSD.addItem('自动', 'auto')
            current_index = 0
            if not auto:
                current_index = 1
            for ssd_folder in config['ssd_folders']:
                text = self.get_folder_display_text(ssd_folder)
                if not auto and ssd_folder == CreatePlotDialog.last_ssd_folder:
                    current_index = self.comboSSD.count()
                self.comboSSD.addItem(text, ssd_folder)
            self.comboSSD.setCurrentIndex(current_index)

            self.load_hdd(last_folder=CreatePlotDialog.last_hdd_folder)

            fpk = ''
            ppk = ''
            nft = ''

            if 'fpk' in config:
                fpk = config['fpk']

            if 'ppk' in config:
                ppk = config['ppk']

            if 'nft' in config:
                nft = config['nft']

            if fpk and ppk:
                self.select_wallet(fpk, ppk, nft)
            elif wallets:
                wallet = wallets[tuple(wallets.keys())[0]]
                self.select_wallet(wallet['fpk'], wallet['ppk'], wallet['nft'])
            self.change_wallet()

            if 'num' in config:
                self.spinNumber.setValue(config['num'])

            if 'thread_num' in config:
                self.spinThreadNum.setValue(config['thread_num'])

            if 'memory_size' in config:
                self.spinMemory.setValue(config['memory_size'])

            if 'specify_count' in config:
                self.checkBoxSpecifyCount.setChecked(config['specify_count'])
                if config['specify_count']:
                    self.spinNumber.setDisabled(False)

            if 'k' in config:
                select_k_combo(config['k'])

            if 'cmdline' in config:
                select_cmdline(config['cmdline'])

        self.comboTemp2.currentIndexChanged.connect(self.slot_change_temp2)
        self.comboBucketNum.currentIndexChanged.connect(self.slot_change_buckets)
        self.comboCmdLine.currentIndexChanged.connect(self.change_cmdline)
        self.comboWallet.currentIndexChanged.connect(self.change_wallet)
        self.change_cmdline()

        self.comboSSD.currentIndexChanged.connect(self.update_form_items)
        self.comboCmdLine.currentIndexChanged.connect(self.update_form_items)
        self.comboHDD.currentIndexChanged.connect(self.update_tip_text)
        self.comboCmdLine.currentIndexChanged.connect(self.update_tip_text)
        self.editNft.textChanged.connect(self.update_tip_text)
        self.checkBoxNoBitfield.stateChanged.connect(self.check_nobitfield)

        self.comboCmdLine.currentIndexChanged.connect(self.slot_create_batch_tasks)
        self.comboSSD.currentIndexChanged.connect(self.slot_create_batch_tasks)
        self.comboHDD.currentIndexChanged.connect(self.slot_create_batch_tasks)
        self.checkBoxNoBitfield.stateChanged.connect(self.slot_create_batch_tasks)
        self.editFpk.textChanged.connect(self.slot_create_batch_tasks)
        self.editPpk.textChanged.connect(self.slot_create_batch_tasks)
        self.comboK.currentIndexChanged.connect(self.slot_create_batch_tasks)
        self.comboBucketNum.currentIndexChanged.connect(self.slot_create_batch_tasks)
        self.spinReservedMemory.valueChanged.connect(self.slot_create_batch_tasks)

        self.update_form_items()
        self.slot_create_batch_tasks()
        self.update_tip_text()

        if not self.modify and self.chia_exe and not CreatePlotDialog.wallets:
            self.reload_wallets()

    def load_hdd(self, last_folder=''):
        config = get_config()
        current_index = 0
        self.comboHDD.addItem('自动', 'auto')
        for hdd_folder_obj in config['hdd_folders']:
            folder = hdd_folder_obj['folder']
            text = self.get_folder_display_text(folder, hdd_folder_obj['new_plot'])
            if last_folder and folder == last_folder:
                current_index = self.comboHDD.count()
            self.comboHDD.addItem(text, folder)
        self.comboHDD.setCurrentIndex(current_index)

    def select_wallet(self, _fpk, _ppk, _nft):
        fp = None
        for _fp in CreatePlotDialog.wallets:
            wallet = CreatePlotDialog.wallets[_fp]
            if wallet['fpk'] == _fpk and wallet['ppk'] == _ppk and wallet['nft'] == _nft:
                fp = _fp
                break

        for i in range(self.comboWallet.count()):
            if self.comboWallet.itemData(i, Qt.UserRole) == fp:
                self.comboWallet.setCurrentIndex(i)

        if fp is None:
            self.custom_fpk = _fpk
            self.custom_ppk = _ppk
            self.custom_nft = _nft

    def get_folder_display_text(self, folder, new_plot=None):
        text = folder
        if os.path.exists(folder):
            usage = get_disk_usage(folder)
            text += f" ({size_to_str(usage.free)}空闲)"
        else:
            text += " (不存在)"

        if new_plot is True:
            text += " (新图)"
        elif new_plot is False:
            text += " (旧图)"

        return text

    def load_temp2(self):
        config = get_config()

        self.comboTemp2.addItem('', '')

        for ssd_folder in config['ssd_folders']:
            self.comboTemp2.addItem(self.get_folder_display_text(ssd_folder), ssd_folder)

        for hdd_folder_obj in config['hdd_folders']:
            folder = hdd_folder_obj['folder']
            self.comboTemp2.addItem(self.get_folder_display_text(folder), folder)

        self.comboTemp2.addItem('手动选择', 'select')

        for selected_folder in CreatePlotDialog.selected_temp2_folders:
            self.comboTemp2.addItem(self.get_folder_display_text(selected_folder), selected_folder)

        self.select_temp2('')

    def load_wallets(self):
        self.labelWallet.setVisible(True)
        self.comboWallet.setVisible(True)
        self.pushReloadWallets.setVisible(True)
        self.comboWallet.clear()
        if not self.chia_exe:
            self.comboWallet.setVisible(False)
            self.labelWallet.setVisible(False)
            self.pushReloadWallets.setVisible(False)
            return
        for fp in CreatePlotDialog.wallets:
            self.comboWallet.addItem(f'公共指纹为 {fp} 的私钥', fp)
        self.comboWallet.addItem('自定义', None)

    def select_temp2(self, folder):
        for i in range(self.comboTemp2.count()):
            if self.comboTemp2.itemData(i, Qt.UserRole) == folder:
                self.comboTemp2.setCurrentIndex(i)
                return

        self.comboTemp2.addItem(self.get_folder_display_text(folder), folder)
        self.comboTemp2.setCurrentIndex(self.comboTemp2.count() - 1)

    def reload_buckets(self):
        self.comboBucketNum.currentIndexChanged.disconnect(self.slot_change_buckets)
        cmdline = self.comboCmdLine.currentData(Qt.UserRole)

        self.comboBucketNum.clear()
        if cmdline == self.get_chia_plot_exe():
            for i in range(4, 16+1):
                self.comboBucketNum.addItem(f"2^{i}={2 **i}" + (' (默认)' if i == 8 else ''), 2 ** i)
        else:
            for i in range(4, 7+1):
                self.comboBucketNum.addItem(f"2^{i}={2 **i}" + (' (默认)' if i == 7 else ''), 2 ** i)

        self.comboBucketNum.currentIndexChanged.connect(self.slot_change_buckets)

    def select_buckets(self, buckets=128):
        for i in range(self.comboBucketNum.count()):
            if self.comboBucketNum.itemData(i, Qt.UserRole) == buckets:
                self.comboBucketNum.setCurrentIndex(i)
                return

    def slot_check_temp2(self):
        checked = self.checkBoxSpecifyTemp2.isChecked()
        self.comboTemp2.setDisabled(not checked)

    def slot_change_temp2(self):
        if self.comboTemp2.currentData(Qt.UserRole) == 'select':
            temp2_folder = QFileDialog.getExistingDirectory(self, '选择目录')
            self.select_temp2(temp2_folder)

    def slot_change_buckets(self):
        buckets = self.comboBucketNum.currentData(Qt.UserRole)
        if buckets is None:
            return

        if self.comboCmdLine.currentData(Qt.UserRole) == self.get_chia_plot_exe():
            self.current_chia_plot_buckets = buckets
        else:
            self.current_buckets = buckets

    def slot_create_batch_tasks(self):
        self.batch_tasks.clear()
        self.treeWidgetTasks.clear()

        if self.comboSSD.currentData() != 'auto':
            self.buttonBox.button(self.buttonBox.Ok).setDisabled(False)
            return

        self.buttonBox.button(self.buttonBox.Ok).setDisabled(True)

        hdd_folder = self.comboHDD.currentData(Qt.UserRole)
        fpk = self.editFpk.toPlainText()
        ppk = self.editPpk.toPlainText()
        k = int(self.comboK.currentData(Qt.UserRole))
        cmdline = self.lineEditCmdLine.text()
        reserved_memory = self.spinReservedMemory.value()

        if not fpk or not ppk or not cmdline:
            return

        if cmdline == self.get_chia_plot_exe():
            QMessageBox.information(self, '提示', '使用多线程chia_plot.exe命令行不支持批量创建任务')
            return

        if hdd_folder != 'auto' and not os.path.exists(hdd_folder):
            QMessageBox.information(self, '提示', '最终目录不存在')
            return

        min_memory_size = 2 ** 30 * 3

        cpu_core = psutil.cpu_count()
        total_memory = psutil.virtual_memory().total
        available_memory = total_memory - reserved_memory * 1024 * 1024

        if available_memory < min_memory_size:
            QMessageBox.information(self, '提示', f'系统可使用的内存小于{size_to_str(min_memory_size)}，无法创建批量任务')
            return

        k_temp_size = get_k_temp_size(k)

        config = get_config()

        total_count = 0
        ssd_count_map = {}

        for ssd_folder in config['ssd_folders']:
            usage = get_disk_usage(ssd_folder)
            if not usage:
                continue
            count = int(usage.total // k_temp_size)
            total_count += count

            ssd_count_map[ssd_folder] = {
                'count': count,
                'reduced': 0,
            }

        if total_count == 0:
            QMessageBox.information(self, '提示', '当前系统资源无法创建任务')
            return

        def reduce_count():
            ssd_to_reduce = None
            last_ssd_reduce_count = 0
            for ssd in ssd_count_map:
                if ssd_count_map[ssd]['count'] == 0:
                    continue
                if ssd_to_reduce is None:
                    ssd_to_reduce = ssd_count_map[ssd]
                    last_ssd_reduce_count = ssd_to_reduce['reduced']
                if ssd_count_map[ssd]['reduced'] < last_ssd_reduce_count:
                    ssd_to_reduce = ssd_count_map[ssd]

            if ssd_to_reduce is None:
                return 0

            if ssd_to_reduce['count'] <= 0:
                return 0

            ssd_to_reduce['count'] -= 1
            ssd_to_reduce['reduced'] += 1

            return total_count - 1

        while available_memory // total_count < min_memory_size:
            total_count = reduce_count()
            if total_count == 0:
                break

        mem_per_task = available_memory // total_count
        thread_per_task = int(cpu_core / total_count + 2)
        if thread_per_task > cpu_core:
            thread_per_task = cpu_core

        if total_count == 0 or mem_per_task < min_memory_size:
            QMessageBox.information(self, '提示', '当前系统资源无法创建任务')
            return

        for ssd_folder in ssd_count_map:
            ssd = ssd_count_map[ssd_folder]
            count = ssd['count']

            if count > 6:
                max_hour = 8
            elif count == 5:
                max_hour = 7
            elif count == 4:
                max_hour = 6
            elif count == 3:
                max_hour = 5
            elif count <= 2:
                max_hour = 4
            else:
                max_hour = 8
            max_time = 60 * 60 * max_hour

            delay_per_task = int(max_time / count)

            for i in range(count):
                self.batch_tasks.append({
                    'ssd_folder': ssd_folder,
                    'hdd_folder': hdd_folder,
                    'memory': mem_per_task,
                    'thread': thread_per_task,
                    'delay': delay_per_task * i,
                })

        self.reload_batch_tasks(self.batch_tasks)

        if self.batch_tasks:
            self.buttonBox.button(self.buttonBox.Ok).setDisabled(False)

    def reload_batch_tasks(self, batch_tasks):
        self.treeWidgetTasks.clear()

        for task in batch_tasks:
            ssd_folder = task['ssd_folder']
            hdd_folder = task['hdd_folder']
            memory = task['memory']
            thread = task['thread']
            delay = task['delay']

            item = QTreeWidgetItem()

            index = 0

            item.setText(index, ssd_folder)

            index += 1
            if hdd_folder == 'auto':
                item.setText(index, '自动')
            else:
                item.setText(index, hdd_folder)

            index += 1
            item.setText(index, size_to_str(memory))

            index += 1
            item.setText(index, f'{thread}')

            index += 1
            item.setText(index, f'{seconds_to_str(delay)}')

            self.treeWidgetTasks.addTopLevelItem(item)

    def update_form_items(self):
        auto = self.comboSSD.currentData(Qt.UserRole) == 'auto'
        chia_plot = self.comboCmdLine.currentData(Qt.UserRole) == self.get_chia_plot_exe()

        self.checkBoxNoBitfield.setVisible(True)
        self.labelNoBitfield.setVisible(True)

        self.comboK.setVisible(True)
        self.labelK.setVisible(True)

        self.spinNumber.setVisible(True)
        self.checkBoxSpecifyCount.setVisible(True)

        self.labelTip.setVisible(not auto)
        self.treeWidgetTasks.setVisible(auto)

        self.spinMemory.setVisible(not auto)
        self.labelMemory.setVisible(not auto)

        self.spinThreadNum.setVisible(not auto)
        self.labelThreadNum.setVisible(not auto)

        self.timeEditDelay.setVisible(not auto)
        self.labelDelay.setVisible(not auto)

        self.spinReservedMemory.setVisible(auto)
        self.labelReserve.setVisible(auto)

        if auto:
            self.checkBoxSpecifyCount.setCheckState(0)
            self.checkBoxSpecifyCount.setVisible(False)
            self.spinNumber.setVisible(False)
            self.setWindowTitle('批量创建任务')
            self.buttonBox.button(self.buttonBox.Ok).setText('批量创建')
        else:
            self.checkBoxSpecifyCount.setVisible(True)
            self.spinNumber.setVisible(True)

            if not self.modify:
                self.setWindowTitle('创建任务')
                self.buttonBox.button(self.buttonBox.Ok).setText('创建')

            self.batch_tasks.clear()
            self.treeWidgetTasks.clear()

        if chia_plot:
            self.spinMemory.setVisible(False)
            self.labelMemory.setVisible(False)

            self.checkBoxNoBitfield.setVisible(False)
            self.labelNoBitfield.setVisible(False)

            self.comboK.setVisible(False)
            self.labelK.setVisible(False)

        self.adjustSize()
        self.update_tip_text()

    def update_tip_text(self):
        ssd_folder = self.comboSSD.currentData(Qt.UserRole)
        hdd_folder = self.comboHDD.currentData(Qt.UserRole)
        num = self.spinNumber.value()
        nft = self.editNft.toPlainText()

        cmdline = self.lineEditCmdLine.text()

        text = '使用'
        if nft and self.is_cmdline_support_nft(cmdline):
            text += '新协议'
        else:
            text += '旧协议'

        text += f'创建一条并发任务，将固态硬盘{ssd_folder}作为临时目录，'
        if hdd_folder == 'auto':
            text += '向所有可用机械硬盘'
        else:
            text += f'向硬盘{hdd_folder} '

        if self.checkBoxSpecifyCount.isChecked():
            text += f'P{num}张图'
        else:
            text += f'P图，直到'
            if hdd_folder == 'auto':
                text += '所有硬盘填满为止'
            else:
                text += '硬盘填满为止'

        self.labelTip.setText(text)

        self.adjustSize()

    def get_builtin_exe(self):
        plat = platform.system()
        if plat == 'Windows':
            folder = 'windows'
        elif plat == 'Darwin':
            folder = 'macos'
        elif plat == 'Linux':
            folder = 'linux'
        else:
            return ''
        exe_cwd = os.path.join(BASE_DIR, 'bin', folder, 'plotter')
        if is_debug():
            return os.path.join(exe_cwd, 'test.exe')
        return os.path.join(exe_cwd, 'ProofOfSpace.exe')

    def get_chia_plot_exe(self):
        plat = platform.system()
        if plat == 'Windows':
            folder = 'windows'
        else:
            return ''
        exe_cwd = os.path.join(BASE_DIR, 'bin', folder, 'plotter')
        return os.path.join(exe_cwd, 'chia_plot.exe')

    def change_cmdline(self):
        cmdline = self.comboCmdLine.currentData(Qt.UserRole)
        if cmdline == 'select':
            chia_exe = QFileDialog.getOpenFileName(self, '选择钱包chia.exe', directory=os.getenv('LOCALAPPDATA'), filter='chia.exe')[0]
            self.lineEditCmdLine.setText(chia_exe)
        else:
            self.lineEditCmdLine.setText(cmdline)

        self.reload_buckets()

        if cmdline == self.get_chia_plot_exe():
            self.select_buckets(self.current_chia_plot_buckets)
        else:
            self.select_buckets(self.current_buckets)

        nft_support = self.is_cmdline_support_nft(cmdline)
        self.labelNft.setVisible(nft_support)
        self.editNft.setVisible(nft_support)

    def is_cmdline_support_nft(self, cmdline):
        if cmdline == self.get_chia_plot_exe():
            return True
        elif self.chia_exe and self.chia_ver and \
                cmdline == self.chia_exe and \
                is_chia_support_new_protocol(self.chia_ver):
            return True
        return False

    def change_wallet(self):
        fp = self.comboWallet.currentData(Qt.UserRole)

        self.editFpk.setDisabled(fp is not None)
        self.editPpk.setDisabled(fp is not None)
        self.editNft.setDisabled(False)

        self.editFpk.setPlainText('')
        self.editPpk.setPlainText('')
        self.editNft.setPlainText('')

        if fp:
            wallet = CreatePlotDialog.wallets[fp]
            fpk, ppk, nft = wallet['fpk'], wallet['ppk'], wallet['nft']
        else:
            fpk = self.custom_fpk
            ppk = self.custom_ppk
            nft = self.custom_nft

        self.editFpk.setPlainText(fpk)
        self.editPpk.setPlainText(ppk)
        self.editNft.setPlainText(nft)

    def reload_wallets(self):
        if not self.chia_exe:
            return

        self.pushReloadWallets.setVisible(False)
        self.labelReloadingWallets.setVisible(True)
        self.comboWallet.setDisabled(True)

        wallet_manager.reload_wallets(self.chia_exe, self.chia_ver)

    def slot_get_wallets(self, wallets):
        fpk = self.editFpk.toPlainText()
        ppk = self.editPpk.toPlainText()
        nft = self.editNft.toPlainText()

        CreatePlotDialog.wallets = wallets
        self.load_wallets()

        self.select_wallet(fpk, ppk, nft)

        self.pushReloadWallets.setVisible(True)
        self.labelReloadingWallets.setVisible(False)
        self.comboWallet.setDisabled(False)

    def check_nobitfield(self, value):
        if value != 0:
            if QMessageBox.information(self, '提示', f'禁止位域会导致P图过程效率低且临时文件大，确定要禁止吗？',
                                       QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                self.checkBoxNoBitfield.setCheckState(0)

    def check_specify_count(self):
        self.spinNumber.setDisabled(not self.checkBoxSpecifyCount.isChecked())

        self.update_tip_text()

    def is_hdd_folder_new_plot(self, hdd_folder):
        config = get_config()
        for hdd_folder_obj in config['hdd_folders']:
            if hdd_folder_obj['folder'] == hdd_folder:
                return hdd_folder_obj['new_plot']
        return False

    def accept_modify(self):
        thread_num = self.spinThreadNum.value()
        memory_size = self.spinMemory.value()
        buckets = self.comboBucketNum.currentData(Qt.UserRole)
        k = int(self.comboK.currentData(Qt.UserRole))
        nobitfield = self.checkBoxNoBitfield.isChecked()
        hdd_folder = self.comboHDD.currentData(Qt.UserRole)

        if self.checkBoxSpecifyTemp2.isChecked():
            temp2_folder = self.comboTemp2.currentData(Qt.UserRole)
        else:
            temp2_folder = ''

        if hdd_folder == 'auto':
            self.task.auto_hdd_folder = True
        else:
            self.task.auto_hdd_folder = False
            self.task.hdd_folder = hdd_folder

        self.task.number_of_thread = thread_num
        self.task.memory_size = memory_size
        self.task.buckets = buckets
        self.task.k = k
        self.task.nobitfield = nobitfield
        self.task.temporary2_folder = temp2_folder

        if self.task.specify_count:
            for sub in self.task.sub_tasks:
                if not sub.finish and not sub.working:
                    if hdd_folder == 'auto':
                        sub.hdd_folder = ''
                    else:
                        sub.hdd_folder = hdd_folder

                    sub.buckets = buckets
                    sub.k = k
                    sub.nobitfield = nobitfield

        super().accept()
        return

    def accept(self) -> None:
        fpk = self.editFpk.toPlainText()
        ppk = self.editPpk.toPlainText()
        nft = self.editNft.toPlainText()
        buckets = self.comboBucketNum.currentData(Qt.UserRole)
        k = int(self.comboK.currentData(Qt.UserRole))
        nobitfield = self.checkBoxNoBitfield.isChecked()
        cmdline = self.lineEditCmdLine.text()

        ssd_folder = self.comboSSD.currentData()
        hdd_folder = self.comboHDD.currentData()

        CreatePlotDialog.last_ssd_folder = ssd_folder
        CreatePlotDialog.last_hdd_folder = hdd_folder

        delayTime = self.timeEditDelay.time()
        delay = delayTime.hour() * 60*60 + delayTime.minute() * 60 + delayTime.second()

        specify_count = self.checkBoxSpecifyCount.isChecked()
        number = self.spinNumber.value()
        thread_num = self.spinThreadNum.value()
        memory_size = self.spinMemory.value()

        if not cmdline:
            QMessageBox.information(self, '提示', '请选择命令行程序')
            return

        if self.checkBoxSpecifyTemp2.isChecked():
            temp2_folder = self.comboTemp2.currentData(Qt.UserRole)

            if not temp2_folder:
                QMessageBox.information(self, '提示', '请选择第二临时目录')
                return
            if not os.path.exists(temp2_folder):
                QMessageBox.information(self, '提示', '第二临时目录不存在')
                return

            if temp2_folder not in CreatePlotDialog.selected_temp2_folders:
                CreatePlotDialog.selected_temp2_folders.append(temp2_folder)
        else:
            temp2_folder = ''

        if not self.is_cmdline_support_nft(cmdline):
            nft = ''

        if nft and (len(nft) != 62 or not nft.startswith('xch')):
            QMessageBox.information(self, '提示', 'NFT合约地址格式错误，请检查')
            return

        if self.modify:
            self.accept_modify()
            return

        if ssd_folder != 'auto' and not os.path.exists(ssd_folder):
            QMessageBox.information(self, '提示', '临时目录不存在')
            return

        if hdd_folder != 'auto' and not os.path.exists(hdd_folder):
            QMessageBox.information(self, '提示', '最终目录不存在')
            return

        if fpk.startswith('0x'):
            fpk = fpk[2:]
        if ppk.startswith('0x'):
            ppk = ppk[2:]

        if not fpk:
            QMessageBox.information(self, '提示', '请输入fpk')
            return

        if not nft and not ppk:
            QMessageBox.information(self, '提示', '请输入ppk或者NFT合约地址')
            return

        new_plot = True
        if cmdline == self.chia_exe and not is_chia_support_new_protocol(self.chia_ver):
            new_plot = False
            if QMessageBox.information(self, '提示', '确定要使用旧协议吗？\n当前的钱包版本不支持新协议，P出的图只能使用旧协议。想要使用新协议，需要升级钱包。',
                                       QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return
        elif not nft:
            new_plot = False
            if QMessageBox.information(self, '提示', '确定要使用旧协议吗？\n没有NFT合约地址，P出的图只能使用旧协议。想要使用新协议，需要到钱包软件中创建NFT合约地址。',
                                       QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return

        if hdd_folder != 'auto':
            hdd_folder_new_plot = self.is_hdd_folder_new_plot(hdd_folder)
            if hdd_folder_new_plot != new_plot:
                def new_old(_new_old):
                    return '新' if _new_old else '旧'
                msg = f'正在创建的是{new_old(new_plot)}图，但是最终目录{hdd_folder}是用来存放{new_old(hdd_folder_new_plot)}图的，请检查。'
                QMessageBox.information(self, '提示', msg)
                return

        if len(fpk) != 96:
            QMessageBox.information(self, '提示', 'fpk格式错误，请检查')
            return
        if ppk and len(ppk) != 96:
            QMessageBox.information(self, '提示', 'ppk格式错误，请检查')
            return

        if not specify_count:
            number = 1

        if ssd_folder == 'auto' and not self.batch_tasks:
            QMessageBox.information(self, '提示', f'当前系统资源无法创建批量任务')
            return

        if hdd_folder != 'auto':
            hdd_usage = get_disk_usage(hdd_folder)

            if hdd_usage is None:
                QMessageBox.information(self, '提示', f'目录{hdd_folder}无法使用')
                return

            k_size = get_k_size(k)
            if not is_debug() and hdd_usage.free < k_size:
                if QMessageBox.information(self, '提示', f'最终目录的空间不足{size_to_str(k_size)}，确定要继续吗？', QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                    return

        config = get_config()

        config['cmdline'] = cmdline
        config['fpk'] = fpk
        config['ppk'] = ppk
        config['nft'] = nft

        if cmdline == self.get_chia_plot_exe():
            config['chia_plot_buckets'] = buckets
        else:
            config['buckets'] = buckets
        config['k'] = k
        config['specify_count'] = specify_count
        config['num'] = number
        config['thread_num'] = thread_num
        config['memory_size'] = memory_size

        save_config()

        self.result.clear()
        if ssd_folder == 'auto':
            for batch_task in self.batch_tasks:
                _ssd_folder = batch_task['ssd_folder']
                _hdd_folder = batch_task['hdd_folder']
                _memory = batch_task['memory']
                _thread = batch_task['thread']
                _delay = batch_task['delay']

                _memory = _memory // 1024 // 1024

                task = self.create_task(cmdline=cmdline, fpk=fpk, ppk=ppk, nft=nft, buckets=buckets, k=k, nobitfield=nobitfield,
                                        ssd_folder=_ssd_folder, hdd_folder=_hdd_folder, temp2_folder=temp2_folder,
                                        specify_count=False,count=1, thread_num=_thread, memory_size=_memory,
                                        delay=_delay)
                if task:
                    self.result.append(task)
        else:
            task = self.create_task(cmdline=cmdline, fpk=fpk, ppk=ppk, nft=nft, buckets=buckets, k=k, nobitfield=nobitfield,
                                    ssd_folder=ssd_folder, hdd_folder=hdd_folder, temp2_folder=temp2_folder,
                                    specify_count=specify_count, count=number, thread_num=thread_num,
                                    memory_size=memory_size, delay=delay)
            if task:
                self.result = [task]

        if not self.result:
            return

        super().accept()

    def create_task(self, cmdline, fpk, ppk, nft, buckets, k, nobitfield, ssd_folder, hdd_folder, temp2_folder, specify_count, count,
                    thread_num, memory_size, delay) -> Optional[PlotTask]:
        temporary_folder = os.path.join(ssd_folder, make_name(12))
        temporary_folder = temporary_folder.replace('\\', '/')

        try:
            os.mkdir(temporary_folder)
        except:
            QMessageBox.information(self, '提示', '创建临时目录失败 %s' % temporary_folder)
            return None

        if temp2_folder:
            temp2_folder = os.path.join(temp2_folder, make_name(12))
            temp2_folder = temp2_folder.replace('\\', '/')

            try:
                os.mkdir(temp2_folder)
            except:
                QMessageBox.information(self, '提示', '创建第二临时目录失败 %s' % temp2_folder)
                return None

        task = PlotTask()

        task.cmdline = cmdline
        if cmdline == self.get_builtin_exe():
            task.plotter_type = PLOTTER_BUILTIN
        elif cmdline == self.chia_exe:
            task.plotter_type = PLOTTER_OFFICIAL
            task.chia_exe_ver = self.chia_ver
        elif cmdline == self.get_chia_plot_exe():
            task.plotter_type = PLOTTER_CHIA_PLOT

        task.create_time = datetime.now()
        task.fpk = fpk
        task.ppk = ppk
        task.nft = nft
        task.buckets = buckets
        task.k = k
        task.nobitfield = nobitfield
        task.ssd_folder = ssd_folder
        if hdd_folder == 'auto':
            task.auto_hdd_folder = True
        else:
            task.auto_hdd_folder = False
            task.hdd_folder = hdd_folder
        task.temporary_folder = temporary_folder
        task.temporary2_folder = temp2_folder
        task.specify_count = specify_count
        task.count = count
        task.number_of_thread = thread_num
        task.memory_size = memory_size
        task.delay_seconds = delay

        if specify_count:
            for i in range(count):
                task.sub_tasks.append(PlotSubTask(task, i))
        else:
            task.sub_tasks.append(PlotSubTask(task, 0))

        return task
