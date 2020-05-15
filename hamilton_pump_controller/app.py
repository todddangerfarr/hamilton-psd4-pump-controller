from PyQt5 import QtWidgets
import sys

from .ui.main_window import MainWindow

import warnings
warnings.filterwarnings("ignore")


def run():
    # instantiate PyQT applicaiton object
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
