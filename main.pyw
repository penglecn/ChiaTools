import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator
import resources
from MainWindow import MainWindow
from config import load_config


if __name__ == '__main__':
    app = QApplication(sys.argv)

    trans = QTranslator()
    trans.load(':/lang/qt_zh_CN.qm')
    app.installTranslator(trans)

    load_config()

    win = MainWindow()
    win.show()

    app.exec()
