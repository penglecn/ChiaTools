from PyQt5.QtWidgets import QWidget, QTreeWidgetItem, QHeaderView, QProgressBar, QMessageBox, QMenu, QFileDialog
from PyQt5.Qt import QBrush, QColor, QModelIndex, QTimerEvent, QCursor
from PyQt5.QtCore import Qt
from ui.PlotWidget import Ui_PlotWidget
from config import save_config, get_config
from utils import size_to_str, delta_to_str, seconds_to_str, make_name
from datetime import datetime, timedelta
from core.plot import PlotTask, PlotSubTask
from CreatePlotDialog import CreatePlotDialog
from TaskOutputDialog import TaskOutputDialog
import os
from subprocess import run
import platform
from core.plot import PlotTaskManager


class PlotWidget(QWidget, Ui_PlotWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.main_window = None

        self.treePlot.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.task_manager = PlotTaskManager()

        self.load_tasks()

        self.task_manager.signalUpdateTask.connect(self.updateTaskStatus)
        self.task_manager.signalMakingPlot.connect(self.onMakingPlot)
        self.task_manager.signalNewPlot.connect(self.onNewPlot)
        self.task_manager.signalNewSubTask.connect(self.onNewSubTask)
        self.task_manager.signalSubTaskDone.connect(self.onSubTaskDone)

        self.outputDialogs = []

        self.treePlot.doubleClicked.connect(self.showTaskOutput)
        self.treePlot.expanded.connect(self.onExpanded)
        self.treePlot.collapsed.connect(self.onCollapsed)
        self.treePlot.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treePlot.customContextMenuRequested.connect(self.showTaskMenu)

        self.checkBoxPhase1Limit.stateChanged.connect(self.checkPhase1Limit)
        self.checkBoxTotalLimit.stateChanged.connect(self.checkTotalLimit)
        self.checkBoxNextWhenFullyComplete.stateChanged.connect(self.checkNextWhenFullyComplete)
        self.spinBoxPhase1Count.valueChanged.connect(self.changePhase1LimitCount)
        self.spinBoxTotalCount.valueChanged.connect(self.changeTotalLimitCount)

        self.buttonCreatePlot.clicked.connect(self.clickCreatePlot)
        self.buttonCreateBatchPlots.clicked.connect(self.clickCreateBatchPlots)

        self.timerIdUpdateTime = self.startTimer(1000)
        self.timerIdSaveTasks = self.startTimer(1000 * 60)

        config = get_config()

        if 'total_limit' in config:
            self.checkBoxTotalLimit.setChecked(config['total_limit'])
        if 'phase1_limit' in config:
            self.checkBoxPhase1Limit.setChecked(config['phase1_limit'])

        if 'total_limit_count' in config:
            self.spinBoxTotalCount.setValue(config['total_limit_count'])
        else:
            config['total_limit_count'] = 1

        if 'phase1_limit_count' in config:
            self.spinBoxPhase1Count.setValue(config['phase1_limit_count'])
        else:
            config['phase1_limit_count'] = 1

        if 'next_when_fully_complete' in config:
            self.checkBoxNextWhenFullyComplete.setChecked(config['next_when_fully_complete'])

    def load_tasks(self):
        if self.treePlot.topLevelItemCount() == 0:
            for task in self.task_manager.tasks:
                self.addTaskItem(task)

    def checkPhase1Limit(self, i):
        config = get_config()
        config['phase1_limit'] = self.checkBoxPhase1Limit.isChecked()
        save_config()

    def checkTotalLimit(self, i):
        config = get_config()
        config['total_limit'] = self.checkBoxTotalLimit.isChecked()
        save_config()

    def checkNextWhenFullyComplete(self, i):
        config = get_config()
        config['next_when_fully_complete'] = self.checkBoxNextWhenFullyComplete.isChecked()
        save_config()

    def changePhase1LimitCount(self):
        config = get_config()
        config['phase1_limit_count'] = self.spinBoxPhase1Count.value()
        save_config()

    def changeTotalLimitCount(self):
        config = get_config()
        config['total_limit_count'] = self.spinBoxTotalCount.value()
        save_config()

    def setMainWindow(self, win):
        self.main_window = win

    def timerEvent(self, event: QTimerEvent) -> None:
        timer = event.timerId()

        if timer == self.timerIdUpdateTime:
            self.updateTaskTimes()
        elif timer == self.timerIdSaveTasks:
            PlotTaskManager.save_tasks()

    def showTaskMenu(self, pos):
        item: QTreeWidgetItem = self.treePlot.itemAt(pos)
        index = self.treePlot.indexAt(pos)
        if not item:
            return
        if not index:
            return

        parent_item = item.parent()

        if parent_item:
            task_item = parent_item
            sub_task_item = item
        else:
            task_item = item
            sub_task_item = None

        task: PlotTask = task_item.data(0, Qt.UserRole)

        if sub_task_item:
            sub_task: PlotSubTask = sub_task_item.data(0, Qt.UserRole)
            working = sub_task.working
        else:
            sub_task: PlotSubTask = task.current_sub_task
            working = task.working

        root_item = sub_task_item is None

        menu = QMenu(self)

        action_detail = menu.addAction(u"查看日志")
        action_modify = None
        action_delete = None
        action_stop = None
        action_suspend = None
        action_suspend_for_30min = None
        action_suspend_for_1h = None
        action_suspend_for_2h = None
        action_suspend_for_3h = None
        action_suspend_for_4h = None
        action_resume = None
        action_continue = None
        action_next_stop = None
        action_locate_temp = None
        action_locate_temp2 = None
        action_clean_temp = None
        action_increase_number = None
        action_reduce_number = None
        action_start_immediately = None
        action_clear_finished = None
        action_export_log = None

        if root_item and (task.specify_count and task.count > 1):
            action_detail.setDisabled(True)

        if task.finish:
            if root_item:
                if task.success:
                    menu.addSeparator()
                    if task.specify_count:
                        action_increase_number = menu.addAction(u"增加数量")
                    else:
                        action_continue = menu.addAction(u"继续")

                menu.addSeparator()
                action_delete = menu.addAction(u"删除")
                if not task.success:
                    if os.path.exists(task.temporary_folder):
                        action_clean_temp = menu.addAction(u"清除临时文件")
        elif working:
            if root_item:
                menu.addSeparator()
                action_modify = menu.addAction(u"编辑")
                menu.addSeparator()

                if task.specify_count:
                    action_increase_number = menu.addAction(u"增加数量")
                    if task.pending_count():
                        action_reduce_number = menu.addAction(u"减少数量")
                else:
                    action_next_stop = menu.addAction(u"下一轮任务停止")
                    action_next_stop.setCheckable(True)
                    action_next_stop.setChecked(task.next_stop)

                if not task.specify_count and task.finished_count:
                    menu.addSeparator()
                    action_clear_finished = menu.addAction(u"清除已完成任务")

            if root_item or sub_task.working:
                menu.addSeparator()
                if task.delay_remain():
                    action_stop = menu.addAction(u"取消")
                else:
                    action_stop = menu.addAction(u"停止")

                if sub_task.suspend:
                    action_resume = menu.addAction(u"继续")
                else:
                    action_suspend = menu.addAction(u"暂停")
                    menu_suspend_for = menu.addMenu(u"暂停时间")
                    action_suspend_for_30min = menu_suspend_for.addAction(u"30分钟")
                    action_suspend_for_1h = menu_suspend_for.addAction(u"1小时")
                    action_suspend_for_2h = menu_suspend_for.addAction(u"2小时")
                    action_suspend_for_3h = menu_suspend_for.addAction(u"3小时")
                    action_suspend_for_4h = menu_suspend_for.addAction(u"4小时")
        else:
            if root_item:
                menu.addSeparator()
                remain = task.delay_remain()
                if remain:
                    action_start_immediately = menu.addAction(u'立即开始')

                action_delete = menu.addAction(u"删除")

        if sub_task_item and sub_task.finish:
            menu.addSeparator()
            action_export_log = menu.addAction(u"导出日志")
        elif not sub_task_item and task.finish:
            menu.addSeparator()
            action_export_log = menu.addAction(u"导出所有日志")

        if os.path.exists(task.temporary_folder) and platform.system() == 'Windows':
            menu.addSeparator()
            action_locate_temp = menu.addAction(u"浏览临时文件")
            if task.temporary2_folder:
                action_locate_temp2 = menu.addAction(u"浏览第二临时文件")

        action = menu.exec(QCursor.pos())

        if action is None:
            return

        if action == action_detail:
            self.showTaskOutput(index)
        elif action == action_export_log:
            if sub_task_item and sub_task.finish:
                log_file = ''
                if sub_task.plot_file:
                    log_file = os.path.splitext(os.path.basename(sub_task.plot_file))[0] + '.log'
                log_file = QFileDialog.getSaveFileName(self, '导出日志', log_file, '日志文件 (*.log *.txt)')[0]
                if not log_file:
                    return
                if not self.exportSubTaskLog(sub_task, log_file=log_file):
                    QMessageBox.information(self, '提示', f'导出文件失败 {log_file}')
                    return

            elif not sub_task_item and task.finish:
                folder = QFileDialog.getExistingDirectory(self, '导出所有日志')
                if not folder:
                    return
                for _sub_task in task.sub_tasks:
                    if _sub_task.plot_file:
                        log_name = os.path.splitext(os.path.basename(sub_task.plot_file))[0] + '.log'
                    else:
                        log_name = make_name(12) + '.log'
                    log_file = os.path.join(folder, log_name)
                    if not self.exportSubTaskLog(_sub_task, log_file=log_file):
                        QMessageBox.information(self, '提示', f'导出文件失败 {log_file}')
                        return

        elif action == action_modify:
            dlg = CreatePlotDialog(task=task)
            if dlg.exec() == dlg.rejected:
                return
            self.task_manager.save_tasks()
            self.updateTaskItem(item, task)
            for sub in task.sub_tasks:
                _sub_item = self.getSubItemFromSubTask(item, sub)
                if _sub_item:
                    self.updateSubTaskItem(_sub_item, sub)
        elif action == action_delete:
            all_files, total_size, temp_plot_size = task.get_temp_files()

            if temp_plot_size:
                if QMessageBox.information(self, '提示', f"检测到临时目录下存在未完成移动的plot文件(.plot.2.tmp)，大小{size_to_str(temp_plot_size)}，建议手动把该文件改名为.plot后移动到最终目录。\n\n确定要删除吗？", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                    return

            if len(all_files):
                if QMessageBox.information(self, '提示', f"确定要删除临时目录吗？\n{len(all_files)}个文件\n{size_to_str(total_size)}GB", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                    return
            if os.path.exists(task.temporary_folder) and not task.remove_temp_folder():
                QMessageBox.warning(self, '提示', '清除临时目录失败！')
                return

            if sub_task and sub_task.worker:
                sub_task.worker.stop()

            self.treePlot.takeTopLevelItem(index.row())
            self.task_manager.remove_task(task)
        elif action == action_clear_finished:
            for sub in task.sub_tasks[:]:
                if sub.finish:
                    _sub_item = self.getSubItemFromSubTask(item, sub)
                    if _sub_item:
                        item.removeChild(_sub_item)
                    task.remove_sub_task(sub)
        elif action == action_stop:
            if QMessageBox.information(self, '提示', "确定要停止任务吗？停止后无法恢复", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return
            if sub_task_item:
                sub_task.worker.stop()
            else:
                for sub in task.sub_tasks:
                    if sub.working:
                        sub.worker.stop()
        elif action == action_suspend:
            if sub_task_item:
                sub_task.worker.suspend()
            else:
                for sub in task.sub_tasks:
                    if sub.working and not sub.worker.copying:
                        sub.worker.suspend()
        elif action == action_suspend_for_30min:
            time_for_suspend = 60*30
            if sub_task_item:
                sub_task.worker.suspend(time_for_suspend)
            else:
                for sub in task.sub_tasks:
                    if sub.working and not sub.worker.copying:
                        sub.worker.suspend(time_for_suspend)
        elif action == action_suspend_for_1h:
            time_for_suspend = 60*60*1
            if sub_task_item:
                sub_task.worker.suspend(time_for_suspend)
            else:
                for sub in task.sub_tasks:
                    if sub.working and not sub.worker.copying:
                        sub.worker.suspend(time_for_suspend)
        elif action == action_suspend_for_2h:
            time_for_suspend = 60*60*2
            if sub_task_item:
                sub_task.worker.suspend(time_for_suspend)
            else:
                for sub in task.sub_tasks:
                    if sub.working and not sub.worker.copying:
                        sub.worker.suspend(time_for_suspend)
        elif action == action_suspend_for_3h:
            time_for_suspend = 60*60*3
            if sub_task_item:
                sub_task.worker.suspend(time_for_suspend)
            else:
                for sub in task.sub_tasks:
                    if sub.working and not sub.worker.copying:
                        sub.worker.suspend(time_for_suspend)
        elif action == action_suspend_for_4h:
            time_for_suspend = 60*60*4
            if sub_task_item:
                sub_task.worker.suspend(time_for_suspend)
            else:
                for sub in task.sub_tasks:
                    if sub.working and not sub.worker.copying:
                        sub.worker.suspend(time_for_suspend)
        elif action == action_resume:
            if sub_task_item:
                sub_task.worker.resume()
            else:
                for sub in task.sub_tasks:
                    if sub.working:
                        sub.worker.resume()
        elif action == action_continue:
            if task.finish:
                task.next_stop = False
                task.do_next()
        elif action == action_next_stop:
            task.next_stop = not task.next_stop
        elif action == action_locate_temp:
            folder = task.temporary_folder.replace('/', '\\')
            run('explorer /select, ' + folder)
        elif action == action_locate_temp2:
            folder = task.temporary2_folder.replace('/', '\\')
            run('explorer /select, ' + folder)
        elif action == action_clean_temp:
            all_files, total_size, temp_plot_size = task.get_temp_files()

            if temp_plot_size:
                if QMessageBox.information(self, '提示', f"检测到临时目录下存在未完成移动的plot文件(.plot.2.tmp)，大小{size_to_str(temp_plot_size)}，建议手动把该文件改名为.plot后移动到最终目录。\n\n确定要删除吗？", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                    return

            if len(all_files) == 0:
                QMessageBox.information(self, '提示', '没有临时文件')
                return
            if QMessageBox.information(self, '提示', f"确定要清除临时文件吗？\n{len(all_files)}个文件\n{size_to_str(total_size)}GB", QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Cancel:
                return
            if not task.delete_temp_files():
                QMessageBox.warning(self, '提示', '清除临时文件失败！')
        elif action == action_increase_number:
            finished = task.finish
            sub_task = task.increase()
            if task.count == 2:
                self.addSubTaskItem(item, task.sub_tasks[0])
            self.addSubTaskItem(item, sub_task)
            if finished:
                task.do_next()
                return
        elif action == action_reduce_number:
            sub_task = task.sub_tasks[-1]
            if sub_task.finish or sub_task.working:
                return
            self.removeSubTaskItem(item, sub_task)
            task.reduce()
            if task.count == 1:
                self.removeSubTaskItem(item, task.sub_tasks[0])
        elif action == action_start_immediately:
            if task.delay_remain():
                task.delay_seconds = 0

        if not sub_task_item:
            sub_task_item = self.getSubItemFromSubTask(item, sub_task)
        if sub_task_item:
            self.updateSubTaskItem(sub_task_item, sub_task)

    def exportSubTaskLog(self, sub_task: PlotSubTask, log_file):
        try:
            f = open(log_file, 'w')
            if not f:
                return
            for log in sub_task.log:
                f.write(log + '\n')
            f.close()

            return True
        except:
            return False

    def onExpanded(self, index: QModelIndex):
        item = self.treePlot.itemFromIndex(index)
        if not item:
            return
        task: PlotTask = item.data(0, Qt.UserRole)
        if not task.specify_count:
            return

        if task.count > 1:
            self.treePlot.setItemWidget(item, 7, None)

    def onCollapsed(self, index: QModelIndex):
        item = self.treePlot.itemFromIndex(index)
        if not item:
            return
        task: PlotTask = item.data(0, Qt.UserRole)
        if not task.specify_count:
            return

        progress = QProgressBar()
        progress.setValue(task.progress)
        self.treePlot.setItemWidget(item, 7, progress)

    def showTaskOutput(self, index: QModelIndex):
        item = self.treePlot.itemFromIndex(index)
        parent_item = item.parent()

        if parent_item:
            task_item = parent_item
            sub_task_item = item
        else:
            task_item = item
            sub_task_item = None

        task = task_item.data(0, Qt.UserRole)

        show_output = True

        if sub_task_item is None and not task.specify_count:
            show_output = True
        elif sub_task_item is None and task.count != 1:
            show_output = False

        if not show_output:
            item.setExpanded(not item.isExpanded())
            return

        if sub_task_item:
            sub_task = sub_task_item.data(0, Qt.UserRole)
        else:
            sub_task = task.current_sub_task

        for d in self.outputDialogs:
            if d.task == task and d.sub_task == sub_task:
                d.activateWindow()
                return

        dlg = TaskOutputDialog(sub_task.worker, task, sub_task)
        dlg.signalClose.connect(self.closeTaskOutputDialog)
        dlg.setWindowFlags(Qt.Dialog | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        dlg.show()

        self.outputDialogs.append(dlg)

    def closeTaskOutputDialog(self, dlg):
        self.outputDialogs.remove(dlg)

    def updateTaskTimes(self):
        count = self.treePlot.topLevelItemCount()
        for i in range(count):
            item = self.treePlot.topLevelItem(i)
            task: PlotTask = item.data(0, Qt.UserRole)
            if not task.finish:
                if task.current_sub_task.suspend:
                    if task.delay_remain():
                        task.delay_seconds += 1
                    elif task.current_sub_task.begin_time:
                        task.current_sub_task.suspended_seconds += 1

                    if task.current_sub_task.suspend_time:
                        if task.current_sub_task.suspend_remain_time <= 0:
                            task.current_sub_task.worker.resume()
                        else:
                            task.current_sub_task.suspend_remain_time -= 1

                self.updateTaskItem(item, task)
                sub_item = self.getSubItemFromSubTask(item, task.current_sub_task)
                if sub_item:
                    self.updateSubTaskItem(sub_item, task.current_sub_task)

    def clickCreateBatchPlots(self):
        self.create_plot(True)

    def clickCreatePlot(self):
        self.create_plot(False)

    def create_plot(self, auto=False):
        config = get_config()
        if 'ssd_folders' not in config or not config['ssd_folders'] or 'hdd_folders' not in config or not config['hdd_folders']:
            QMessageBox.information(self, '提示', '请先配置硬盘')
            return

        dlg = CreatePlotDialog(parent=self, task=None, auto=auto)
        if dlg.exec() == dlg.Rejected:
            return

        for task in dlg.result:
            self.task_manager.add_task(task)

            self.addTaskItem(task)

            task.start()

    def onMakingPlot(self, task: PlotTask, sub_task: PlotSubTask):
        pass

    def onNewPlot(self, task: PlotTask, sub_task: PlotSubTask):
        pass

    def onNewSubTask(self, task: PlotTask, sub_task: PlotSubTask):
        pass

    def onSubTaskDone(self, task: PlotTask, sub_task: PlotSubTask):
        if not task.specify_count:
            item = self.getItemFromTask(task)
            if item:
                self.addSubTaskItem(item, sub_task)

    def restartMine(self, log=''):
        if not self.main_window:
            return

        self.main_window.tabHPoolMineWidget.restartMine(log)
        self.main_window.tabHuobiPoolMineWidget.restartMine(log)

    def updateTaskStatus(self, task: PlotTask, sub_task: PlotSubTask):
        item = self.getItemFromTask(task)
        if not item:
            return

        self.updateTaskItem(item, task)

        # if not task.specify_count:
        sub_item = self.getSubItemFromSubTask(item, sub_task)
        if sub_item:
            self.updateSubTaskItem(sub_item, sub_task)

    def getItemFromTask(self, task: PlotTask):
        for i in range(self.treePlot.topLevelItemCount()):
            item = self.treePlot.topLevelItem(i)
            if item.data(0, Qt.UserRole) == task:
                return item
        return None

    def getSubItemFromSubTask(self, item: QTreeWidgetItem, sub_task: PlotSubTask):
        for i in range(item.childCount()):
            sub_item = item.child(i)
            if sub_item.data(0, Qt.UserRole) == sub_task:
                return sub_item
        return None

    def addTaskItem(self, task: PlotTask):
        item = QTreeWidgetItem()
        item.setData(0, Qt.UserRole, task)

        self.treePlot.addTopLevelItem(item)

        progress = QProgressBar()
        progress.setValue(task.progress)

        if task.specify_count:
            if task.count > 1:
                for sub in task.sub_tasks:
                    self.addSubTaskItem(item, sub)
            else:
                self.treePlot.setItemWidget(item, 7, progress)
            item.setExpanded(True)
        else:
            sub_tasks = task.sub_tasks
            if not task.success:
                sub_tasks = task.sub_tasks[0:-2]
            for sub in sub_tasks:
                if sub.finish and sub.success:
                    self.addSubTaskItem(item, sub)
            self.treePlot.setItemWidget(item, 7, progress)

        self.updateTaskItem(item, task)

        return item

    def addSubTaskItem(self, item: QTreeWidgetItem, sub_task: PlotSubTask):
        sub_item = QTreeWidgetItem()
        sub_item.setData(0, Qt.UserRole, sub_task)
        item.addChild(sub_item)
        self.treePlot.setItemWidget(sub_item, 7, QProgressBar())
        self.updateSubTaskItem(sub_item, sub_task)

    def removeSubTaskItem(self, item: QTreeWidgetItem, sub_task: PlotSubTask):
        sub_item = self.getSubItemFromSubTask(item, sub_task)
        if sub_item:
            sub_item.removeChild(sub_item)

    def updateTaskItem(self, item: QTreeWidgetItem, task: PlotTask):
        index = 0

        item.setText(index, task.ssd_folder)

        index += 1
        if task.auto_hdd_folder:
            if task.specify_count or not task.current_sub_task.hdd_folder:
                item.setText(index, '自动')
            else:
                item.setText(index, f'{task.current_sub_task.hdd_folder}(自动)')
        else:
            item.setText(index, task.hdd_folder)

        index += 1
        delay = task.delay_remain()
        item.setText(index, task.status)
        item.setBackground(index, QBrush(QColor('#ffffff')))
        item.setForeground(index, QBrush(QColor(0, 0, 0)))

        if task.finish:
            if task.success:
                color = QColor('#50c350')
            else:
                color = QColor('#e86363')
            item.setBackground(index, QBrush(color))
            item.setForeground(index, QBrush(QColor(255, 255, 255)))
        elif task.suspend:
            if task.current_sub_task.suspend_time:
                item.setText(index, f'暂停{seconds_to_str(task.current_sub_task.suspend_remain_time)}')
            else:
                item.setText(index, '已暂停')
        elif task.abnormal:
            item.setBackground(index, QBrush(QColor('#ffb949')))
            item.setForeground(index, QBrush(QColor(255, 255, 255)))
        elif delay:
            item.setText(index, '等待%s' % seconds_to_str(delay))

        index += 1
        if task.specify_count:
            item.setText(index, '%d/%d' % (task.current_task_index + 1, task.count))
        else:
            if task.success:
                item.setText(index, '%d' % task.count)
            else:
                item.setText(index, '%d' % (task.count - 1))

        index += 1
        if task.begin_time:
            item.setText(index, task.begin_time.strftime('%Y-%m-%d %H:%M:%S'))
        else:
            item.setText(index, '--')

        index += 1
        if task.begin_time:
            end_time = task.end_time
            if not end_time:
                end_time = datetime.now()
            delta = end_time - task.begin_time - timedelta(seconds=task.suspended_seconds)
            item.setText(index, delta_to_str(delta))
        else:
            item.setText(index, '--')

        index += 1
        memory_used = task.memory_used
        item.setText(index, size_to_str(memory_used) if memory_used else '--')

        index += 1
        if task.specify_count and item.isExpanded() and task.count > 1:
            self.treePlot.setItemWidget(item, index, None)
        else:
            progress: QProgressBar = self.treePlot.itemWidget(item, index)
            if not progress:
                progress = QProgressBar()
                self.treePlot.setItemWidget(item, index, progress)
            progress.setValue(task.progress)

    def updateSubTaskItem(self, item: QTreeWidgetItem, task: PlotSubTask):
        index = 0

        item.setText(index, '')

        index += 1
        item.setText(index, task.hdd_folder)

        index += 1
        item.setText(index, task.status)
        item.setBackground(index, QBrush(QColor('#ffffff')))
        item.setForeground(index, QBrush(QColor(0, 0, 0)))

        if task.finish:
            if task.success:
                color = QColor('#50c350')
            else:
                color = QColor('#e86363')
            item.setBackground(index, QBrush(color))
            item.setForeground(index, QBrush(QColor(255, 255, 255)))
        elif task.suspend:
            if task.suspend_time:
                item.setText(index, f'暂停{seconds_to_str(task.suspend_remain_time)}')
            else:
                item.setText(index, '已暂停')
        elif task.abnormal:
            item.setBackground(index, QBrush(QColor('#ffb949')))
            item.setForeground(index, QBrush(QColor(255, 255, 255)))

        index += 1
        item.setText(index, '%d' % (task.index + 1))

        index += 1
        if task.begin_time:
            item.setText(index, task.begin_time.strftime('%Y-%m-%d %H:%M:%S'))
        else:
            item.setText(index, '--')

        index += 1
        if task.begin_time:
            end_time = task.end_time
            if not end_time:
                end_time = datetime.now()
            delta = end_time - task.begin_time - timedelta(seconds=task.suspended_seconds)
            item.setText(index, delta_to_str(delta))
        else:
            item.setText(index, '--')

        index += 1
        memory_used = task.memory_used
        item.setText(index, size_to_str(memory_used) if memory_used and not task.finish else '--')

        index += 1
        progress: QProgressBar = self.treePlot.itemWidget(item, index)
        if progress:
            progress.setValue(task.progress)
