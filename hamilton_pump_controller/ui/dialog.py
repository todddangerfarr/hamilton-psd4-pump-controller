from PyQt5 import QtWidgets, uic
import os


class Dialog(QtWidgets.QDialog):
    def __init__(self, ui_file_path, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        uic.loadUi(
            os.path.dirname(os.path.abspath(__file__)) + ui_file_path, self)
        self.centerOnScreen()

    def centerOnScreen(self):
        '''centerOnScreen() Centers the window on the screen.'''
        frame_geo = self.frameGeometry()
        screen = QtWidgets.QApplication.desktop().screenNumber(
            QtWidgets.QApplication.desktop().cursor().pos())
        ctr = QtWidgets.QApplication.desktop().screenGeometry(screen).center()
        frame_geo.moveCenter(ctr)
        self.move(frame_geo.topLeft())
