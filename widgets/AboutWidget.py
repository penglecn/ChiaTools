from PyQt5.QtWidgets import QWidget
from ui.AboutWidget import Ui_AboutWidget


class AboutWidget(QWidget, Ui_AboutWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
