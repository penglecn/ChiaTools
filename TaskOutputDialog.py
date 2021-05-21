# coding: utf-8
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.Qt import pyqtSignal
from ui.TaskOutputDialog import Ui_TaskOutputDialog
from core.plot import PlotTask, PlotSubTask, PlotWorker


class TaskOutputDialog(QDialog, Ui_TaskOutputDialog):
    signalClose = pyqtSignal(QDialog)

    def __init__(self, worker: PlotWorker, task: PlotTask, sub_task: PlotSubTask, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.task: PlotTask = task
        self.sub_task: PlotSubTask = sub_task
        self.worker: PlotWorker = worker

        self.setWindowTitle('Plot任务: ' + self.task.temporary_folder)

        for log in self.sub_task.log:
            self.edit.append(log)

        if self.worker:
            self.worker.signalTaskOutput.connect(self.slotOutput)

    def slotOutput(self, task: PlotTask, sub_task: PlotSubTask, text):
        if task == self.task and sub_task == self.sub_task:
            self.edit.append(text)

    def reject(self):
        self.close()

    def closeEvent(self, event) -> None:
        if self.worker:
            self.worker.signalTaskOutput.disconnect(self.slotOutput)

        event.accept()

        self.signalClose.emit(self)
