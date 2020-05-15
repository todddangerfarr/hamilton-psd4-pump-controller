from PyQt5 import QtWidgets, uic
import os


class MoveDialog(QtWidgets.QDialog):
    def __init__(self, df=None, file_loc=None, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.ui = uic.loadUi(
                    os.path.dirname(os.path.abspath(__file__))
                    + '/ui_files/add_move_dialog.ui',
                    self
                )
